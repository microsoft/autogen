'''!
 * Copyright (c) 2020-2021 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in the
 * project root for license information.
'''
import time
from typing import Callable, Optional
import warnings
from functools import partial
import numpy as np
from scipy.sparse import issparse
from sklearn.model_selection import train_test_split, RepeatedStratifiedKFold, \
    RepeatedKFold, GroupKFold, TimeSeriesSplit
from sklearn.utils import shuffle
import pandas as pd
import logging

from .ml import compute_estimator, train_estimator, get_estimator_class, \
    get_classification_objective
from .config import (
    MIN_SAMPLE_TRAIN, MEM_THRES, RANDOM_SEED,
    SMALL_LARGE_THRES, CV_HOLDOUT_THRESHOLD, SPLIT_RATIO, N_SPLITS,
    SAMPLE_MULTIPLY_FACTOR)
from .data import concat
from . import tune
from .training_log import training_log_reader, training_log_writer

logger = logging.getLogger(__name__)
logger_formatter = logging.Formatter(
    '[%(name)s: %(asctime)s] {%(lineno)d} %(levelname)s - %(message)s',
    '%m-%d %H:%M:%S')

try:
    import mlflow
except ImportError:
    mlflow = None


class SearchState:

    @property
    def search_space(self):
        return self._search_space_domain

    @property
    def estimated_cost4improvement(self):
        return max(self.time_best_found - self.time_best_found_old,
                   self.total_time_used - self.time_best_found)

    def __init__(self, learner_class, data_size, task, starting_point=None):
        self.init_eci = learner_class.cost_relative2lgbm()
        self._search_space_domain = {}
        self.init_config = {}
        self.low_cost_partial_config = {}
        self.cat_hp_cost = {}
        self.data_size = data_size
        self.ls_ever_converged = False
        self.learner_class = learner_class
        search_space = learner_class.search_space(
            data_size=data_size, task=task)
        for name, space in search_space.items():
            assert 'domain' in space
            self._search_space_domain[name] = space['domain']
            if 'init_value' in space:
                self.init_config[name] = space['init_value']
            if 'low_cost_init_value' in space:
                self.low_cost_partial_config[name] = space[
                    'low_cost_init_value']
            if 'cat_hp_cost' in space:
                self.cat_hp_cost[name] = space['cat_hp_cost']
            # if a starting point is provided, set the init config to be
            # the starting point provided
            if starting_point is not None and starting_point.get(name) is not None:
                self.init_config[name] = starting_point[name]
        self._hp_names = list(self._search_space_domain.keys())
        self.search_alg = None
        self.best_config = None
        self.best_loss = self.best_loss_old = np.inf
        self.total_time_used = 0
        self.total_iter = 0
        self.base_eci = None
        self.time_best_found = 0
        self.time2eval_best = 0
        self.time2eval_best_old = 0
        self.trained_estimator = None
        self.sample_size = None
        self.trial_time = 0

    def update(self, result, time_used, save_model_history=False):
        if result:
            config = result['config']
            if config and 'FLAML_sample_size' in config:
                self.sample_size = config['FLAML_sample_size']
            else:
                self.sample_size = self.data_size
            obj = result['val_loss']
            train_loss = result['train_loss']
            time2eval = result['time_total_s']
            trained_estimator = result['trained_estimator']
            del result['trained_estimator']     # free up RAM
        else:
            obj, time2eval, trained_estimator = np.inf, 0.0, None
            train_loss = config = None
        self.trial_time = time2eval
        self.total_time_used += time_used
        self.total_iter += 1

        if self.base_eci is None:
            self.base_eci = time_used
        if (obj is not None) and (self.best_loss is None or obj < self.best_loss):
            self.best_loss_old = self.best_loss if self.best_loss < np.inf \
                else 2 * obj
            self.best_loss = obj
            self.time_best_found_old = self.time_best_found
            self.time_best_found = self.total_time_used
            self.iter_best_found = self.total_iter
            self.best_config = config
            self.best_config_sample_size = self.sample_size
            self.best_config_train_time = time_used
            if time2eval:
                self.time2eval_best_old = self.time2eval_best
                self.time2eval_best = time2eval
            if self.trained_estimator and trained_estimator and \
                self.trained_estimator != trained_estimator and \
                    not save_model_history:
                self.trained_estimator.cleanup()
            if trained_estimator:
                self.trained_estimator = trained_estimator
        self.train_loss, self.val_loss, self.config = train_loss, obj, config

    def get_hist_config_sig(self, sample_size, config):
        config_values = tuple([config[k] for k in self._hp_names])
        config_sig = str(sample_size) + '_' + str(config_values)
        return config_sig

    def est_retrain_time(self, retrain_sample_size):
        assert self.best_config_sample_size is not None, \
            'need to first get best_config_sample_size'
        return (self.time2eval_best * retrain_sample_size
                / self.best_config_sample_size)


class AutoMLState:

    def _prepare_sample_train_data(self, sample_size):
        full_size = len(self.y_train)
        sampled_weight = None
        if sample_size <= full_size:
            if isinstance(self.X_train, pd.DataFrame):
                sampled_X_train = self.X_train.iloc[:sample_size]
            else:
                sampled_X_train = self.X_train[:sample_size]
            sampled_y_train = self.y_train[:sample_size]
            weight = self.fit_kwargs.get('sample_weight')
            if weight is not None:
                sampled_weight = weight[:sample_size]
        else:
            sampled_X_train = self.X_train_all
            sampled_y_train = self.y_train_all
            if 'sample_weight' in self.fit_kwargs:
                sampled_weight = self.sample_weight_all
        return sampled_X_train, sampled_y_train, sampled_weight

    def _compute_with_config_base(self,
                                  estimator,
                                  config_w_resource):
        if 'FLAML_sample_size' in config_w_resource:
            sample_size = int(config_w_resource['FLAML_sample_size'])
        else:
            sample_size = self.data_size
        sampled_X_train, sampled_y_train, sampled_weight = \
            self._prepare_sample_train_data(sample_size)
        if sampled_weight is not None:
            weight = self.fit_kwargs['sample_weight']
            self.fit_kwargs['sample_weight'] = sampled_weight
        else:
            weight = None
        config = config_w_resource.copy()
        if 'FLAML_sample_size' in config:
            del config['FLAML_sample_size']
        time_left = self.time_budget - self.time_from_start
        budget = time_left if sample_size == self.data_size else \
            time_left / 2 * sample_size / self.data_size

        trained_estimator, val_loss, train_loss, _, pred_time = \
            compute_estimator(
                sampled_X_train,
                sampled_y_train,
                self.X_val,
                self.y_val,
                self.weight_val,
                min(budget, self.train_time_limit),
                self.kf,
                config,
                self.task,
                estimator,
                self.eval_method,
                self.metric,
                self.best_loss,
                self.n_jobs,
                self.learner_classes.get(estimator),
                self.log_training_metric,
                self.fit_kwargs)
        result = {
            'pred_time': pred_time,
            'wall_clock_time': time.time() - self._start_time_flag,
            'train_loss': train_loss,
            'val_loss': val_loss,
            'trained_estimator': trained_estimator
        }
        if sampled_weight is not None:
            self.fit_kwargs['sample_weight'] = weight
        #     tune.report(**result)
        return result

    def _train_with_config(
        self, estimator, config_w_resource, sample_size=None
    ):
        config = config_w_resource.copy()
        if 'FLAML_sample_size' in config:
            if not sample_size:
                sample_size = config['FLAML_sample_size']
            del config['FLAML_sample_size']
        assert sample_size is not None
        sampled_X_train, sampled_y_train, sampled_weight = \
            self._prepare_sample_train_data(sample_size)
        if sampled_weight is not None:
            weight = self.fit_kwargs['sample_weight']
            self.fit_kwargs['sample_weight'] = sampled_weight
        else:
            weight = None
        budget = None if self.time_budget is None else (
            self.time_budget - self.time_from_start)
        estimator, train_time = train_estimator(
            sampled_X_train,
            sampled_y_train,
            config,
            self.task,
            estimator,
            self.n_jobs,
            self.learner_classes.get(estimator),
            budget,
            self.fit_kwargs)
        if sampled_weight is not None:
            self.fit_kwargs['sample_weight'] = weight
        return estimator, train_time


def size(state: AutoMLState, config: dict) -> float:
    '''Size function

    Returns:
        The mem size in bytes for a config
    '''
    config = config.get('ml', config)
    estimator = config['learner']
    learner_class = state.learner_classes.get(estimator)
    return learner_class.size(config)


class AutoML:
    '''The AutoML class

    Example:

        .. code-block:: python

            automl = AutoML()
            automl_settings = {
                "time_budget": 60,
                "metric": 'accuracy',
                "task": 'classification',
                "log_file_name": 'test/mylog.log',
            }
            automl.fit(X_train = X_train, y_train = y_train,
                **automl_settings)

    '''

    from .version import __version__

    def __init__(self):
        self._track_iter = 0
        self._state = AutoMLState()
        self._state.learner_classes = {}

    @property
    def model_history(self):
        '''A dictionary of iter->model, storing the models when
        the best model is updated each time.
        '''
        return self._model_history

    @property
    def config_history(self):
        '''A dictionary of iter->(estimator, config, time),
        storing the best estimator, config, and the time when the best
        model is updated each time.
        '''
        return self._config_history

    @property
    def model(self):
        '''An object with `predict()` and `predict_proba()` method (for
        classification), storing the best trained model.
        '''
        if self._trained_estimator:
            return self._trained_estimator
        else:
            return None

    def best_model_for_estimator(self, estimator_name):
        '''Return the best model found for a particular estimator

        Args:
            estimator_name: a str of the estimator's name

        Returns:
            An object with `predict()` and `predict_proba()` method (for
        classification), storing the best trained model for estimator_name.
        '''
        if estimator_name in self._search_states:
            state = self._search_states[estimator_name]
            if hasattr(state, 'trained_estimator'):
                return state.trained_estimator
        return None

    @property
    def best_estimator(self):
        '''A string indicating the best estimator found.'''
        return self._best_estimator

    @property
    def best_iteration(self):
        '''An integer of the iteration number where the best
        config is found.'''
        return self._best_iteration

    @property
    def best_config(self):
        '''A dictionary of the best configuration.'''
        return self._search_states[self._best_estimator].best_config

    @property
    def best_config_per_estimator(self):
        '''A dictionary of all estimators' best configuration.'''
        return {e: e_search_state.best_config for e, e_search_state in
                self._search_states.items()}

    @property
    def best_loss(self):
        '''A float of the best loss found
        '''
        return self._state.best_loss

    @property
    def best_config_train_time(self):
        '''A float of the seconds taken by training the
        best config.'''
        return self._search_states[self._best_estimator].best_config_train_time

    @property
    def classes_(self):
        '''A list of n_classes elements for class labels.'''
        if self._label_transformer:
            return self._label_transformer.classes_.tolist()
        if self._trained_estimator:
            return self._trained_estimator.classes_.tolist()
        return None

    def predict(self, X_test, freq=None):
        '''Predict label from features.

        Args:
            X_test: A numpy array of featurized instances, shape n * m,
                or a pandas dataframe with one column with timestamp values
                for 'forecasting' task.
            freq: str or pandas offset, default=None | The frequency of the
                time-series.

        Returns:
            A numpy array of shape n * 1 - - each element is a predicted class
            label for an instance.
        '''
        if self._trained_estimator is None:
            warnings.warn(
                "No estimator is trained. Please run fit with enough budget.")
            return None
        X_test = self._preprocess(X_test)
        if self._state.task == 'forecast':
            X_test_df = pd.DataFrame(X_test)
            X_test_col = list(X_test.columns)[0]
            X_test_df = X_test_df.rename(columns={X_test_col: 'ds'})
            y_pred = self._trained_estimator.predict(X_test_df, freq=freq)
        else:
            y_pred = self._trained_estimator.predict(X_test)
        if y_pred.ndim > 1 and isinstance(y_pred, np.ndarray):
            y_pred = y_pred.flatten()
        if self._label_transformer:
            return self._label_transformer.inverse_transform(pd.Series(
                y_pred))
        else:
            return y_pred

    def predict_proba(self, X_test):
        '''Predict the probability of each class from features, only works for
        classification problems.

        Args:
            X_test: A numpy array of featurized instances, shape n * m.

        Returns:
            A numpy array of shape n * c. c is the  # classes. Each element at
            (i, j) is the probability for instance i to be in class j.
        '''
        X_test = self._preprocess(X_test)
        proba = self._trained_estimator.predict_proba(X_test)
        return proba

    def _preprocess(self, X):
        if issparse(X):
            X = X.tocsr()
        if self._transformer:
            X = self._transformer.transform(X)
        return X

    def _validate_data(self, X_train_all, y_train_all, dataframe, label,
                       X_val=None, y_val=None):
        if self._state.task == 'forecast':
            if dataframe is not None and label is not None:
                dataframe = dataframe.copy()
                dataframe = dataframe.rename(columns={label[0]: 'ds', label[1]: 'y'})
            elif dataframe is not None:
                if ('ds' not in dataframe) or ('y' not in dataframe):
                    raise ValueError(
                        'For forecasting task, Dataframe must have columns "ds" and "y" '
                        'with the dates and values respectively.'
                    )
            elif (X_train_all is not None) and (y_train_all is not None):
                dataframe = pd.DataFrame(X_train_all)
                time_col = list(dataframe.columns)[0]
                dataframe = dataframe.rename(columns={time_col: 'ds'})
                dataframe['y'] = pd.Series(y_train_all)
                X_train_all = None
                y_train_all = None
            label = 'y'

        if X_train_all is not None and y_train_all is not None:
            if not (isinstance(X_train_all, np.ndarray) or issparse(X_train_all)
                    or isinstance(X_train_all, pd.DataFrame)):
                raise ValueError(
                    "X_train_all must be a numpy array, a pandas dataframe, "
                    "or Scipy sparse matrix.")
            if not (isinstance(y_train_all, np.ndarray)
                    or isinstance(y_train_all, pd.Series)):
                raise ValueError(
                    "y_train_all must be a numpy array or a pandas series.")
            if X_train_all.size == 0 or y_train_all.size == 0:
                raise ValueError("Input data must not be empty.")
            if isinstance(y_train_all, np.ndarray):
                y_train_all = y_train_all.flatten()
            if X_train_all.shape[0] != y_train_all.shape[0]:
                raise ValueError(
                    "# rows in X_train must match length of y_train.")
            self._df = isinstance(X_train_all, pd.DataFrame)
            self._nrow, self._ndim = X_train_all.shape
            X, y = X_train_all, y_train_all
        elif dataframe is not None and label is not None:
            if not isinstance(dataframe, pd.DataFrame):
                raise ValueError("dataframe must be a pandas DataFrame")
            if label not in dataframe.columns:
                raise ValueError("label must a column name in dataframe")
            self._df = True
            X = dataframe.drop(columns=label)
            self._nrow, self._ndim = X.shape
            y = dataframe[label]
        else:
            raise ValueError(
                "either X_train+y_train or dataframe+label are required")
        if issparse(X_train_all) or self._state.task == 'forecast':
            self._transformer = self._label_transformer = False
            self._X_train_all, self._y_train_all = X, y
        else:
            from .data import DataTransformer
            self._transformer = DataTransformer()
            self._X_train_all, self._y_train_all = \
                self._transformer.fit_transform(X, y, self._state.task)
            self._label_transformer = self._transformer.label_transformer
        self._sample_weight_full = self._state.fit_kwargs.get('sample_weight')
        if X_val is not None and y_val is not None:
            if not (isinstance(X_val, np.ndarray) or issparse(X_val)
                    or isinstance(X_val, pd.DataFrame)):
                raise ValueError(
                    "X_val must be None, a numpy array, a pandas dataframe, "
                    "or Scipy sparse matrix.")
            if not (isinstance(y_val, np.ndarray)
                    or isinstance(y_val, pd.Series)):
                raise ValueError(
                    "y_val must be None, a numpy array or a pandas series.")
            if X_val.size == 0 or y_val.size == 0:
                raise ValueError(
                    "Validation data are expected to be nonempty. "
                    "Use None for X_val and y_val if no validation data.")
            if isinstance(y_val, np.ndarray):
                y_val = y_val.flatten()
            if X_val.shape[0] != y_val.shape[0]:
                raise ValueError("# rows in X_val must match length of y_val.")
            if self._transformer:
                self._state.X_val = self._transformer.transform(X_val)
            else:
                self._state.X_val = X_val
            if self._label_transformer:
                self._state.y_val = self._label_transformer.transform(y_val)
            else:
                self._state.y_val = y_val
        else:
            self._state.X_val = self._state.y_val = None

    def _prepare_data(self,
                      eval_method,
                      split_ratio,
                      n_splits,
                      period=None):
        X_val, y_val = self._state.X_val, self._state.y_val
        if issparse(X_val):
            X_val = X_val.tocsr()
        X_train_all, y_train_all = self._X_train_all, self._y_train_all
        if issparse(X_train_all):
            X_train_all = X_train_all.tocsr()
        if self._state.task in ('binary:logistic', 'multi:softmax') \
                and self._state.fit_kwargs.get('sample_weight') is None \
                and self._split_type != 'time':
            # logger.info(f"label {pd.unique(y_train_all)}")
            label_set, counts = np.unique(y_train_all, return_counts=True)
            # augment rare classes
            rare_threshld = 20
            rare = counts < rare_threshld
            rare_label, rare_counts = label_set[rare], counts[rare]
            for i, label in enumerate(rare_label):
                count = rare_count = rare_counts[i]
                rare_index = y_train_all == label
                n = len(y_train_all)
                while count < rare_threshld:
                    if self._df:
                        X_train_all = concat(X_train_all,
                                             X_train_all.iloc[:n].loc[rare_index])
                    else:
                        X_train_all = concat(X_train_all,
                                             X_train_all[:n][rare_index, :])
                    if isinstance(y_train_all, pd.Series):
                        y_train_all = concat(y_train_all,
                                             y_train_all.iloc[:n].loc[rare_index])
                    else:
                        y_train_all = np.concatenate([y_train_all,
                                                      y_train_all[:n][rare_index]])
                    count += rare_count
                logger.info(
                    f"class {label} augmented from {rare_count} to {count}")
        SHUFFLE_SPLIT_TYPES = ['uniform', 'stratified']
        if self._split_type in SHUFFLE_SPLIT_TYPES:
            if self._sample_weight_full is not None:
                X_train_all, y_train_all, self._state.sample_weight_all = \
                    shuffle(X_train_all, y_train_all, self._sample_weight_full,
                            random_state=RANDOM_SEED)
                self._state.fit_kwargs[
                    'sample_weight'] = self._state.sample_weight_all
            elif hasattr(self._state, 'groups') and self._state.groups is not None:
                X_train_all, y_train_all, self._state.groups = shuffle(
                    X_train_all, y_train_all, self._state.groups,
                    random_state=RANDOM_SEED)
            else:
                X_train_all, y_train_all = shuffle(
                    X_train_all, y_train_all, random_state=RANDOM_SEED)
        if self._df:
            X_train_all.reset_index(drop=True, inplace=True)
            if isinstance(y_train_all, pd.Series):
                y_train_all.reset_index(drop=True, inplace=True)

        X_train, y_train = X_train_all, y_train_all
        if X_val is None:
            # if eval_method = holdout, make holdout data
            if eval_method == 'holdout' and self._split_type == 'time':
                if 'period' in self._state.fit_kwargs:
                    num_samples = X_train_all.shape[0]
                    split_idx = num_samples - self._state.fit_kwargs.get('period')
                    X_train = X_train_all[:split_idx]
                    y_train = y_train_all[:split_idx]
                    X_val = X_train_all[split_idx:]
                    y_val = y_train_all[split_idx:]
                else:
                    if 'sample_weight' in self._state.fit_kwargs:
                        X_train, X_val, y_train, y_val, self._state.fit_kwargs[
                            'sample_weight'], self._state.weight_val = \
                            train_test_split(
                                X_train_all,
                                y_train_all,
                                self._state.fit_kwargs['sample_weight'],
                                test_size=split_ratio,
                                shuffle=False)
                    else:
                        X_train, X_val, y_train, y_val = train_test_split(
                            X_train_all,
                            y_train_all,
                            test_size=split_ratio,
                            shuffle=False)
            elif self._state.task != 'regression' and eval_method == 'holdout':
                # for classification, make sure the labels are complete in both
                # training and validation data
                label_set, first = np.unique(y_train_all, return_index=True)
                rest = []
                last = 0
                first.sort()
                for i in range(len(first)):
                    rest.extend(range(last, first[i]))
                    last = first[i] + 1
                rest.extend(range(last, len(y_train_all)))
                X_first = X_train_all.iloc[first] if self._df else X_train_all[
                    first]
                X_rest = X_train_all.iloc[rest] if self._df else X_train_all[rest]
                y_rest = y_train_all.iloc[rest] if isinstance(
                    y_train_all, pd.Series) else y_train_all[rest]
                stratify = y_rest if self._split_type == 'stratified' else \
                    None
                if 'sample_weight' in self._state.fit_kwargs:
                    X_train, X_val, y_train, y_val, weight_train, weight_val = \
                        train_test_split(
                            X_rest,
                            y_rest,
                            self._state.fit_kwargs['sample_weight'][rest],
                            test_size=split_ratio,
                            random_state=RANDOM_SEED)
                    weight1 = self._state.fit_kwargs['sample_weight'][first]
                    self._state.weight_val = concat(weight1, weight_val)
                    self._state.fit_kwargs['sample_weight'] = concat(
                        weight1, weight_train)
                else:
                    X_train, X_val, y_train, y_val = train_test_split(
                        X_rest,
                        y_rest,
                        test_size=split_ratio,
                        stratify=stratify,
                        random_state=RANDOM_SEED)
                X_train = concat(X_first, X_train)
                y_train = concat(
                    label_set, y_train) if self._df else np.concatenate(
                    [label_set, y_train])
                X_val = concat(X_first, X_val)
                y_val = concat(label_set, y_val) if self._df else \
                    np.concatenate([label_set, y_val])
            elif eval_method == 'holdout' and self._state.task == 'regression':
                if 'sample_weight' in self._state.fit_kwargs:
                    X_train, X_val, y_train, y_val, self._state.fit_kwargs[
                        'sample_weight'], self._state.weight_val = \
                        train_test_split(
                            X_train_all,
                            y_train_all,
                            self._state.fit_kwargs['sample_weight'],
                            test_size=split_ratio,
                            random_state=RANDOM_SEED)
                else:
                    X_train, X_val, y_train, y_val = train_test_split(
                        X_train_all,
                        y_train_all,
                        test_size=split_ratio,
                        random_state=RANDOM_SEED)
        self._state.data_size = X_train.shape[0]
        self.data_size_full = len(y_train_all)
        self._state.X_train, self._state.y_train, self._state.X_val, \
            self._state.y_val = (X_train, y_train, X_val, y_val)
        self._state.X_train_all = X_train_all
        self._state.y_train_all = y_train_all
        if hasattr(self._state, 'groups') and self._state.groups is not None:
            logger.info("Using GroupKFold")
            assert len(self._state.groups) == y_train_all.size, \
                "the length of groups must match the number of examples"
            assert len(np.unique(self._state.groups)) >= n_splits, \
                "the number of groups must be equal or larger than n_splits"
            self._state.kf = GroupKFold(n_splits)
            self._state.kf.groups = self._state.groups
        elif self._split_type == "stratified":
            logger.info("Using StratifiedKFold")
            assert y_train_all.size >= n_splits, (
                f"{n_splits}-fold cross validation"
                f" requires input data with at least {n_splits} examples.")
            assert y_train_all.size >= 2 * n_splits, (
                f"{n_splits}-fold cross validation with metric=r2 "
                f"requires input data with at least {n_splits*2} examples.")
            self._state.kf = RepeatedStratifiedKFold(
                n_splits=n_splits, n_repeats=1, random_state=RANDOM_SEED)
        elif self._split_type == "time":
            logger.info("Using TimeSeriesSplit")
            if self._state.task == 'forecast':
                self._state.kf = TimeSeriesSplit(
                    n_splits=n_splits, test_size=self._state.fit_kwargs.get('period'))
            else:
                self._state.kf = TimeSeriesSplit(n_splits=n_splits)
        else:
            logger.info("Using RepeatedKFold")
            self._state.kf = RepeatedKFold(
                n_splits=n_splits, n_repeats=1, random_state=RANDOM_SEED)

    def add_learner(self,
                    learner_name,
                    learner_class):
        '''Add a customized learner

        Args:
            learner_name: A string of the learner's name
            learner_class: A subclass of flaml.model.BaseEstimator
        '''
        self._state.learner_classes[learner_name] = learner_class

    def get_estimator_from_log(self, log_file_name, record_id, task):
        '''Get the estimator from log file

        Args:
            log_file_name: A string of the log file name
            record_id: An integer of the record ID in the file,
                0 corresponds to the first trial
            task: A string of the task type,
                'binary', 'multi', or 'regression'

        Returns:
            An estimator object for the given configuration
        '''

        with training_log_reader(log_file_name) as reader:
            record = reader.get_record(record_id)
            estimator = record.learner
            config = record.config

        estimator, _ = train_estimator(
            None, None, config, task, estimator,
            estimator_class=self._state.learner_classes.get(estimator))
        return estimator

    def retrain_from_log(self,
                         log_file_name,
                         X_train=None,
                         y_train=None,
                         dataframe=None,
                         label=None,
                         time_budget=0,
                         task='classification',
                         eval_method='auto',
                         split_ratio=SPLIT_RATIO,
                         n_splits=N_SPLITS,
                         split_type="stratified",
                         n_jobs=1,
                         train_best=True,
                         train_full=False,
                         record_id=-1,
                         **fit_kwargs):
        '''Retrain from log file

        Args:
            time_budget: A float number of the time budget in seconds
            log_file_name: A string of the log file name
            X_train: A numpy array of training data in shape n*m
            y_train: A numpy array of labels in shape n*1
            task: A string of the task type, e.g.,
                'classification', 'regression'
            eval_method: A string of resampling strategy, one of
                ['auto', 'cv', 'holdout']
            split_ratio: A float of the validation data percentage for holdout
            n_splits: An integer of the number of folds for cross-validation
            n_jobs: An integer of the number of threads for training
            train_best: A boolean of whether to train the best config in the
                time budget; if false, train the last config in the budget
            train_full: A boolean of whether to train on the full data. If true,
                eval_method and sample_size in the log file will be ignored
            record_id: the ID of the training log record from which the model will
                be retrained. By default `record_id = -1` which means this will be
                ignored. `record_id = 0` corresponds to the first trial, and
                when `record_id >= 0`, `time_budget` will be ignored.
            **fit_kwargs: Other key word arguments to pass to fit() function of
                the searched learners, such as sample_weight
        '''
        self._state.task = task
        self._state.fit_kwargs = fit_kwargs
        self._validate_data(X_train, y_train, dataframe, label)

        logger.info('log file name {}'.format(log_file_name))

        best_config = None
        best_val_loss = float('+inf')
        best_estimator = None
        sample_size = None
        time_used = 0.0
        training_duration = 0
        best = None
        with training_log_reader(log_file_name) as reader:
            if record_id >= 0:
                best = reader.get_record(record_id)
            else:
                for record in reader.records():
                    time_used = record.wall_clock_time
                    if time_used > time_budget:
                        break
                    training_duration = time_used
                    val_loss = record.validation_loss
                    if val_loss <= best_val_loss or not train_best:
                        if val_loss == best_val_loss and train_best:
                            size = record.sample_size
                            if size > sample_size:
                                best = record
                                best_val_loss = val_loss
                                sample_size = size
                        else:
                            best = record
                            size = record.sample_size
                            best_val_loss = val_loss
                            sample_size = size
                if not training_duration:
                    from .model import BaseEstimator as Estimator
                    self._trained_estimator = Estimator()
                    self._trained_estimator.model = None
                    return training_duration
        if not best:
            return
        best_estimator = best.learner
        best_config = best.config
        sample_size = len(self._y_train_all) if train_full \
            else best.sample_size

        logger.info(
            'estimator = {}, config = {}, #training instances = {}'.format(
                best_estimator, best_config, sample_size))
        # Partially copied from fit() function
        # Initilize some attributes required for retrain_from_log
        self._state.task = task
        if self._state.task == 'classification':
            self._state.task = get_classification_objective(
                len(np.unique(self._y_train_all)))
            assert split_type in ["stratified", "uniform", "time"]
            self._split_type = split_type
        elif self._state.task == 'regression':
            if split_type in ["uniform", "time"]:
                self._split_type = split_type
            else:
                self._split_type = "uniform"
        elif self._state.task == 'forecast':
            self._split_type = "time"
        if record_id >= 0:
            eval_method = 'cv'
        elif eval_method == 'auto':
            eval_method = self._decide_eval_method(time_budget)
        self.modelcount = 0
        self._prepare_data(eval_method, split_ratio, n_splits)
        self._state.time_budget = None
        self._state.n_jobs = n_jobs
        self._trained_estimator = self._state._train_with_config(
            best_estimator, best_config, sample_size)[0]
        logger.info('retrain from log succeeded')
        return training_duration

    def _decide_eval_method(self, time_budget):
        if self._state.X_val is not None:
            return 'holdout'
        nrow, dim = self._nrow, self._ndim
        if nrow * dim / 0.9 < SMALL_LARGE_THRES * (
                time_budget / 3600) and nrow < CV_HOLDOUT_THRESHOLD:
            # time allows or sampling can be used and cv is necessary
            return 'cv'
        else:
            return 'holdout'

    @property
    def search_space(self) -> dict:
        '''Search space
        Must be called after fit(...) (use max_iter=0 to prevent actual fitting)

        Returns:
            A dict of the search space
        '''
        estimator_list = self.estimator_list
        if len(estimator_list) == 1:
            estimator = estimator_list[0]
            space = self._search_states[estimator].search_space.copy()
            space['learner'] = estimator
            return space
        choices = []
        for estimator in estimator_list:
            space = self._search_states[estimator].search_space.copy()
            space['learner'] = estimator
            choices.append(space)
        return {'ml': tune.choice(choices)}

    @property
    def low_cost_partial_config(self) -> dict:
        '''Low cost partial config

        Returns:
            A dict.
            (a) if there is only one estimator in estimator_list, each key is a
            hyperparameter name.
            (b) otherwise, it is a nested dict with 'ml' as the key, and
            a list of the low_cost_partial_configs as the value, corresponding
            to each learner's low_cost_partial_config; the estimator index as
            an integer corresponding to the cheapest learner is appeneded to the
            list at the end.

        '''
        if len(self.estimator_list) == 1:
            estimator = self.estimator_list[0]
            c = self._search_states[estimator].low_cost_partial_config
            return c
        else:
            configs = []
            for estimator in self.estimator_list:
                c = self._search_states[estimator].low_cost_partial_config
                configs.append(c)
            configs.append(np.argmin([
                self._state.learner_classes.get(estimator).cost_relative2lgbm()
                for estimator in self.estimator_list]))
            config = {'ml': configs}
        return config

    @property
    def cat_hp_cost(self) -> dict:
        '''Categorical hyperparameter cost

        Returns:
            A dict.
            (a) if there is only one estimator in estimator_list, each key is a
            hyperparameter name.
            (b) otherwise, it is a nested dict with 'ml' as the key, and
            a list of the cat_hp_cost's as the value, corresponding
            to each learner's cat_hp_cost; the cost relative to lgbm for each
            learner (as a list itself) is appended to the list at the end.

        '''
        if len(self.estimator_list) == 1:
            estimator = self.estimator_list[0]
            c = self._search_states[estimator].cat_hp_cost
            return c
        else:
            configs = []
            for estimator in self.estimator_list:
                c = self._search_states[estimator].cat_hp_cost
                configs.append(c)
            configs.append([
                self._state.learner_classes.get(estimator).cost_relative2lgbm()
                for estimator in self.estimator_list])
            config = {'ml': configs}
        return config

    @property
    def points_to_evaluate(self) -> dict:
        '''Initial points to evaluate

        Returns:
            A list of dicts. Each dict is the initial point for each learner
        '''
        points = []
        for estimator in self.estimator_list:
            config = self._search_states[estimator].init_config
            config['learner'] = estimator
            if len(self.estimator_list) > 1:
                points.append({'ml': config})
            else:
                points.append(config)
        return points

    @property
    def prune_attr(self) -> Optional[str]:
        '''Attribute for pruning

        Returns:
            A string for the sample size attribute or None
        '''
        return 'FLAML_sample_size' if self._sample else None

    @property
    def min_resource(self) -> Optional[float]:
        '''Attribute for pruning

        Returns:
            A float for the minimal sample size or None
        '''
        return MIN_SAMPLE_TRAIN if self._sample else None

    @property
    def max_resource(self) -> Optional[float]:
        '''Attribute for pruning

        Returns:
            A float for the maximal sample size or None
        '''
        return self._state.data_size if self._sample else None

    @property
    def trainable(self) -> Callable[[dict], Optional[float]]:
        '''Training function

        Returns:
            A function that evaluates each config and returns the loss
        '''
        self._state.time_from_start = 0
        for estimator in self.estimator_list:
            search_state = self._search_states[estimator]
            if not hasattr(search_state, 'training_function'):
                search_state.training_function = partial(
                    AutoMLState._compute_with_config_base,
                    self._state, estimator)
        states = self._search_states
        mem_res = self._mem_thres

        def train(config: dict):
            sample_size = config.get('FLAML_sample_size')
            config = config.get('ml', config).copy()
            if sample_size:
                config['FLAML_sample_size'] = sample_size
            estimator = config['learner']
            # check memory constraints before training
            if states[estimator].learner_class.size(config) <= mem_res:
                del config['learner']
                result = states[estimator].training_function(config)
                return result
            else:
                return {'pred_time': 0,
                        'wall_clock_time': None,
                        'train_loss': np.inf,
                        'val_loss': np.inf,
                        'trained_estimator': None
                        }
        return train

    @property
    def metric_constraints(self) -> list:
        '''Metric constraints

        Returns:
            A list of the metric constraints
        '''
        constraints = []
        if np.isfinite(self._pred_time_limit):
            constraints.append(
                ('pred_time', '<=', self._pred_time_limit))
        return constraints

    def fit(self,
            X_train=None,
            y_train=None,
            dataframe=None,
            label=None,
            metric='auto',
            task='classification',
            n_jobs=-1,
            log_file_name='flaml.log',
            estimator_list='auto',
            time_budget=60,
            max_iter=1000000,
            sample=True,
            ensemble=False,
            eval_method='auto',
            log_type='better',
            model_history=False,
            split_ratio=SPLIT_RATIO,
            n_splits=N_SPLITS,
            log_training_metric=False,
            mem_thres=MEM_THRES,
            pred_time_limit=np.inf,
            train_time_limit=np.inf,
            X_val=None,
            y_val=None,
            sample_weight_val=None,
            groups=None,
            verbose=1,
            retrain_full=True,
            split_type="stratified",
            learner_selector='sample',
            hpo_method=None,
            starting_points={},
            seed=None,
            n_concurrent_trials=1,
            **fit_kwargs):
        '''Find a model for a given task

        Args:
            X_train: A numpy array or a pandas dataframe of training data in
                shape (n, m). For 'forecast' task, X_train should contain a
                single column of timestamps.
            y_train: A numpy array or a pandas series of labels in shape (n, ).
            dataframe: A dataframe of training data including label column.
                For 'forecast' task, dataframe must be specified and should
                have two columns: timestamp and value.
            label: A str of the label column name for 'classification' or
                'regression' task, e.g., 'label';
                or a tuple of strings for timestamp and value columns for
                'forecasting' task, e.g., ('timestamp', 'value').
                Note: If X_train and y_train are provided,
                dataframe and label are ignored;
                If not, dataframe and label must be provided.
            metric: A string of the metric name or a function,
                e.g., 'accuracy', 'roc_auc', 'roc_auc_ovr', 'roc_auc_ovo',
                'f1', 'micro_f1', 'macro_f1', 'log_loss', 'mae', 'mse', 'r2',
                'mape'.
                If passing a customized metric function, the function needs to
                have the follwing signature:

                .. code-block:: python

                    def custom_metric(
                        X_test, y_test, estimator, labels,
                        X_train, y_train, weight_test=None, weight_train=None
                    ):
                        return metric_to_minimize, metrics_to_log

                which returns a float number as the minimization objective,
                and a tuple of floats or a dictionary as the metrics to log.
            task: A string of the task type, e.g.,
                'classification', 'regression', 'forecast'.
            n_jobs: An integer of the number of threads for training.
            log_file_name: A string of the log file name.
            estimator_list: A list of strings for estimator names, or 'auto'
                e.g.,

                .. code-block:: python

                    ['lgbm', 'xgboost', 'catboost', 'rf', 'extra_tree']

            time_budget: A float number of the time budget in seconds.
            max_iter: An integer of the maximal number of iterations.
            sample: A boolean of whether to sample the training data during
                search.
            eval_method: A string of resampling strategy, one of
                ['auto', 'cv', 'holdout'].
            split_ratio: A float of the valiation data percentage for holdout.
            n_splits: An integer of the number of folds for cross - validation.
            log_type: A string of the log type, one of
                ['better', 'all'].
                'better' only logs configs with better loss than previos iters
                'all' logs all the tried configs.
            model_history: A boolean of whether to keep the history of best
                models in the history property. Make sure memory is large
                enough if setting to True.
            log_training_metric: A boolean of whether to log the training
                metric for each model.
            mem_thres: A float of the memory size constraint in bytes.
            pred_time_limit: A float of the prediction latency constraint in seconds.
            train_time_limit: A float of the training time constraint in seconds.
            X_val: None or a numpy array or a pandas dataframe of validation data.
            y_val: None or a numpy array or a pandas series of validation labels.
            sample_weight_val: None or a numpy array of the sample weight of
                validation data.
            groups: None or an array-like of shape (n,) | Group labels for the
                samples used while splitting the dataset into train/valid set.
            verbose: int, default=1 | Controls the verbosity, higher means more
                messages.
            retrain_full: bool or str, default=True | whether to retrain the
                selected model on the full training data when using holdout.
                True - retrain only after search finishes; False - no retraining;
                'budget' - do best effort to retrain without violating the time
                budget.
            hpo_method: str or None, default=None | The hyperparameter
                optimization method. When it is None, CFO is used.
                No need to set when using flaml's default search space or using
                a simple customized search space. When set to 'bs', BlendSearch
                is used. BlendSearch can be tried when the search space is
                complex, for example, containing multiple disjoint, discontinuous
                subspaces. When set to 'random' and the argument 'n_concurrent_trials'
                is larger than 1, RandomSearch is used.
            starting_points: A dictionary to specify the starting hyperparameter
                config for the estimators.
                Keys are the name of the estimators, and values are the starting
                hyperparamter configurations for the corresponding estimators.
            seed: int or None, default=None | The random seed for np.random.
            n_concurrent_trials: [Experimental] int, default=1 | The number of
                concurrent trials. For n_concurrent_trials > 1, installation of
                ray is required: `pip install flaml[ray]`.
            **fit_kwargs: Other key word arguments to pass to fit() function of
                the searched learners, such as sample_weight. Include period as
                a key word argument for 'forecast' task.
        '''
        self._state._start_time_flag = self._start_time_flag = time.time()
        self._state.task = task
        self._state.log_training_metric = log_training_metric
        self._state.fit_kwargs = fit_kwargs
        self._state.weight_val = sample_weight_val
        self._state.groups = groups

        self._validate_data(X_train, y_train, dataframe, label, X_val, y_val)
        self._search_states = {}  # key: estimator name; value: SearchState
        self._random = np.random.RandomState(RANDOM_SEED)
        if seed is not None:
            np.random.seed(seed)
        self._learner_selector = learner_selector
        old_level = logger.getEffectiveLevel()
        self.verbose = verbose
        if verbose == 0:
            logger.setLevel(logging.WARNING)
        if self._state.task == 'classification':
            self._state.task = get_classification_objective(
                len(np.unique(self._y_train_all)))
            assert split_type in ["stratified", "uniform", "time"]
            self._split_type = split_type
        elif self._state.task == 'regression':
            if split_type in ["uniform", "time"]:
                self._split_type = split_type
            else:
                self._split_type = "uniform"
        elif self._state.task == 'forecast':
            if split_type is not None and split_type != 'time':
                raise ValueError(
                    "split_type must be 'time' when task is 'forecast'.")
            self._split_type = "time"
            if self._state.fit_kwargs.get('period') is None:
                raise TypeError(
                    "missing 1 required argument for 'forecast' task: 'period'.")
        if eval_method == 'auto' or self._state.X_val is not None:
            eval_method = self._decide_eval_method(time_budget)
        self._state.eval_method = eval_method
        if (not mlflow or not mlflow.active_run()) and not logger.handlers:
            # Add the console handler.
            _ch = logging.StreamHandler()
            _ch.setFormatter(logger_formatter)
            logger.addHandler(_ch)
        logger.info("Evaluation method: {}".format(eval_method))

        self._retrain_in_budget = retrain_full == 'budget' and (
            eval_method == 'holdout' and self._state.X_val is None)
        self._retrain_final = retrain_full is True and (
            eval_method == 'holdout' and self._state.X_val is None) or (
                eval_method == 'cv')
        if self._state.task != 'forecast':
            self._prepare_data(eval_method, split_ratio, n_splits)
        else:
            self._prepare_data(eval_method, split_ratio, n_splits,
                               period=self._state.fit_kwargs['period'])
        self._sample = sample and eval_method != 'cv' and (
            MIN_SAMPLE_TRAIN * SAMPLE_MULTIPLY_FACTOR < self._state.data_size)
        if 'auto' == metric:
            if 'binary' in self._state.task:
                metric = 'roc_auc'
            elif 'multi' in self._state.task:
                metric = 'log_loss'
            elif self._state.task == 'forecast':
                metric = 'mape'
            else:
                metric = 'r2'
        self._state.metric = metric
        if metric in ['r2', 'accuracy', 'roc_auc', 'roc_auc_ovr', 'roc_auc_ovo',
                      'f1', 'ap', 'micro_f1', 'macro_f1']:
            error_metric = f"1-{metric}"
        elif isinstance(metric, str):
            error_metric = metric
        else:
            error_metric = 'customized metric'
        logger.info(f'Minimizing error metric: {error_metric}')

        if 'auto' == estimator_list:
            if self._state.task == 'forecast':
                estimator_list = ['fbprophet', 'arima', 'sarimax']
            else:
                estimator_list = [
                    'lgbm', 'rf', 'catboost', 'xgboost', 'extra_tree']
                if 'regression' != self._state.task:
                    estimator_list += ['lrl1']
        for estimator_name in estimator_list:
            if estimator_name not in self._state.learner_classes:
                self.add_learner(
                    estimator_name,
                    get_estimator_class(self._state.task, estimator_name))
        # set up learner search space
        for estimator_name in estimator_list:
            estimator_class = self._state.learner_classes[estimator_name]
            estimator_class.init()
            self._search_states[estimator_name] = SearchState(
                learner_class=estimator_class,
                data_size=self._state.data_size, task=self._state.task,
                starting_point=starting_points.get(estimator_name)
            )
        logger.info("List of ML learners in AutoML Run: {}".format(
            estimator_list))
        self.estimator_list = estimator_list
        self._hpo_method = hpo_method or 'cfo'
        self._state.time_budget = time_budget
        self._active_estimators = estimator_list.copy()
        self._ensemble = ensemble
        self._max_iter = max_iter
        self._mem_thres = mem_thres
        self._pred_time_limit = pred_time_limit
        self._state.train_time_limit = train_time_limit
        self._log_type = log_type
        self.split_ratio = split_ratio
        self._save_model_history = model_history
        self._state.n_jobs = n_jobs
        self._n_concurrent_trials = n_concurrent_trials
        if log_file_name:
            with training_log_writer(log_file_name) as save_helper:
                self._training_log = save_helper
                self._search()
        else:
            self._training_log = None
            self._search()
        if self._best_estimator:
            logger.info("fit succeeded")
            logger.info(f"Time taken to find the best model: {self._time_taken_best_iter}")
            if self._time_taken_best_iter >= time_budget * 0.7 and not all(
                state.search_alg and state.search_alg.searcher.is_ls_ever_converged
                for state in self._search_states.values()
            ):
                logger.warn("Time taken to find the best model is {0:.0f}% of the "
                            "provided time budget and not all estimators' hyperparameter "
                            "search converged. Consider increasing the time budget.".format(
                                self._time_taken_best_iter / time_budget * 100))

        if verbose == 0:
            logger.setLevel(old_level)

    def _search_parallel(self):
        try:
            from ray import __version__ as ray_version
            assert ray_version >= '1.0.0'
            import ray
            from ray.tune.suggest import ConcurrencyLimiter
        except (ImportError, AssertionError):
            raise ImportError(
                "n_concurrent_trial > 1 requires installation of ray. "
                "Please run pip install flaml[ray]")
        if self._hpo_method in ('cfo', 'grid'):
            from flaml import CFO as SearchAlgo
        elif 'optuna' == self._hpo_method:
            from ray.tune.suggest.optuna import OptunaSearch as SearchAlgo
        elif 'bs' == self._hpo_method:
            from flaml import BlendSearch as SearchAlgo
        elif 'cfocat' == self._hpo_method:
            from flaml.searcher.cfo_cat import CFOCat as SearchAlgo
        elif 'random' == self._hpo_method:
            from ray.tune.suggest import BasicVariantGenerator as SearchAlgo
            from ray.tune.sample import Domain as RayDomain
            from .tune.sample import Domain
        else:
            raise NotImplementedError(
                f"hpo_method={self._hpo_method} is not recognized. "
                "'cfo' and 'bs' are supported.")
        if self._hpo_method == 'random':
            # Any point in points_to_evaluate must consist of hyperparamters
            # that are tunable, which can be identified by checking whether
            # the corresponding value in the search space is an instance of
            # the 'Domain' class from flaml or ray.tune
            points_to_evaluate = self.points_to_evaluate.copy()
            to_del = []
            for k, v in self.search_space.items():
                if not (isinstance(v, Domain) or isinstance(v, RayDomain)):
                    to_del.append(k)
            for k in to_del:
                for p in points_to_evaluate:
                    del p[k]

            search_alg = SearchAlgo(max_concurrent=self._n_concurrent_trials,
                                    points_to_evaluate=points_to_evaluate
                                    )
        else:
            search_alg = SearchAlgo(
                metric='val_loss',
                space=self.search_space,
                low_cost_partial_config=self.low_cost_partial_config,
                points_to_evaluate=self.points_to_evaluate,
                cat_hp_cost=self.cat_hp_cost,
                prune_attr=self.prune_attr,
                min_resource=self.min_resource,
                max_resource=self.max_resource,
                config_constraints=[(partial(size, self._state), '<=', self._mem_thres)],
                metric_constraints=self.metric_constraints)
            search_alg = ConcurrencyLimiter(search_alg, self._n_concurrent_trials)
        self._state.time_from_start = time.time() - self._start_time_flag
        time_left = self._state.time_budget - self._state.time_from_start
        search_alg.set_search_properties(None, None, config={
            'time_budget_s': time_left})
        resources_per_trial = {
            "cpu": self._state.n_jobs} if self._state.n_jobs > 1 else None
        analysis = ray.tune.run(
            self.trainable, search_alg=search_alg, config=self.search_space,
            metric='val_loss', mode='min', resources_per_trial=resources_per_trial,
            time_budget_s=self._state.time_budget, num_samples=self._max_iter)
        # logger.info([trial.last_result for trial in analysis.trials])
        trials = sorted((trial for trial in analysis.trials if trial.last_result
                        and trial.last_result['wall_clock_time'] is not None),
                        key=lambda x: x.last_result['wall_clock_time'])
        for _track_iter, trial in enumerate(trials):
            result = trial.last_result
            better = False
            if result:
                config = result['config']
                estimator = config.get('ml', config)['learner']
                search_state = self._search_states[estimator]
                search_state.update(result, 0, self._save_model_history)
                if result['wall_clock_time'] is not None:
                    self._state.time_from_start = result['wall_clock_time']
                if search_state.sample_size == self._state.data_size:
                    self._iter_per_learner[estimator] += 1
                    if not self._fullsize_reached:
                        self._fullsize_reached = True
                if search_state.best_loss < self._state.best_loss:
                    self._state.best_loss = search_state.best_loss
                    self._best_estimator = estimator
                    self._config_history[_track_iter] = (
                        self._best_estimator, config, self._time_taken_best_iter)
                    if self._save_model_history:
                        self._model_history[_track_iter] = search_state.trained_estimator
                    self._trained_estimator = search_state.trained_estimator
                    self._best_iteration = _track_iter
                    self._time_taken_best_iter = self._state.time_from_start
                    better = True
                    self._search_states[estimator].best_config = config
                if (better or self._log_type == 'all') and self._training_log:
                    self._training_log.append(
                        self._iter_per_learner[estimator],
                        search_state.train_loss,
                        search_state.trial_time,
                        self._state.time_from_start,
                        search_state.val_loss,
                        config,
                        self._state.best_loss,
                        search_state.best_config,
                        estimator,
                        search_state.sample_size)

    def _search_sequential(self):
        try:
            from ray import __version__ as ray_version
            assert ray_version >= '1.0.0'
            from ray.tune.suggest import ConcurrencyLimiter
        except (ImportError, AssertionError):
            from .searcher.suggestion import ConcurrencyLimiter
        if self._hpo_method in ('cfo', 'grid'):
            from flaml import CFO as SearchAlgo
        elif 'optuna' == self._hpo_method:
            try:
                assert ray_version >= '1.0.0'
                from ray.tune.suggest.optuna import OptunaSearch as SearchAlgo
            except (ImportError, AssertionError):
                from .searcher.suggestion import OptunaSearch as SearchAlgo
        elif 'bs' == self._hpo_method:
            from flaml import BlendSearch as SearchAlgo
        elif 'cfocat' == self._hpo_method:
            from flaml.searcher.cfo_cat import CFOCat as SearchAlgo
        else:
            raise NotImplementedError(
                f"hpo_method={self._hpo_method} is not recognized. "
                "'cfo' and 'bs' are supported.")

        est_retrain_time = next_trial_time = 0
        best_config_sig = None
        better = True  # whether we find a better model in one trial
        if self._ensemble:
            self.best_model = {}
        for self._track_iter in range(self._max_iter):
            if self._estimator_index is None:
                estimator = self._active_estimators[0]
            else:
                estimator = self._select_estimator(self._active_estimators)
                if not estimator:
                    break
            logger.info(
                f"iteration {self._track_iter}, current learner {estimator}")
            search_state = self._search_states[estimator]
            self._state.time_from_start = time.time() - self._start_time_flag
            time_left = self._state.time_budget - self._state.time_from_start
            budget_left = time_left if not self._retrain_in_budget or better or (
                not self.best_estimator) or self._search_states[
                self.best_estimator].sample_size < self._state.data_size \
                else time_left - est_retrain_time
            if not search_state.search_alg:
                search_state.training_function = partial(
                    AutoMLState._compute_with_config_base,
                    self._state, estimator)
                search_space = search_state.search_space
                if self._sample:
                    prune_attr = 'FLAML_sample_size'
                    min_resource = MIN_SAMPLE_TRAIN
                    max_resource = self._state.data_size
                else:
                    prune_attr = min_resource = max_resource = None
                learner_class = self._state.learner_classes.get(estimator)
                if 'grid' == self._hpo_method:  # for synthetic exp only
                    points_to_evaluate = []
                    space = search_space
                    keys = list(space.keys())
                    domain0, domain1 = space[keys[0]], space[keys[1]]
                    for x1 in range(domain0.lower, domain0.upper + 1):
                        for x2 in range(domain1.lower, domain1.upper + 1):
                            points_to_evaluate.append({
                                keys[0]: x1,
                                keys[1]: x2,
                            })
                    self._max_iter_per_learner = len(points_to_evaluate)
                    low_cost_partial_config = None
                else:
                    points_to_evaluate = [search_state.init_config]
                    low_cost_partial_config = search_state.low_cost_partial_config
                if self._hpo_method in ('bs', 'cfo', 'grid', 'cfocat'):
                    algo = SearchAlgo(
                        metric='val_loss', mode='min', space=search_space,
                        points_to_evaluate=points_to_evaluate,
                        low_cost_partial_config=low_cost_partial_config,
                        cat_hp_cost=search_state.cat_hp_cost,
                        prune_attr=prune_attr,
                        min_resource=min_resource,
                        max_resource=max_resource,
                        config_constraints=[
                            (learner_class.size, '<=', self._mem_thres)
                        ],
                        metric_constraints=self.metric_constraints,
                    )
                else:
                    algo = SearchAlgo(
                        metric='val_loss', mode='min', space=search_space,
                        points_to_evaluate=points_to_evaluate,
                    )
                search_state.search_alg = ConcurrencyLimiter(algo,
                                                             max_concurrent=1)
                # search_state.search_alg = algo
            else:
                search_space = None
                if self._hpo_method in ('bs', 'cfo', 'cfocat'):
                    search_state.search_alg.set_search_properties(
                        metric=None, mode=None,
                        config={
                            'metric_target': self._state.best_loss,
                        },
                    )
            start_run_time = time.time()
            analysis = tune.run(
                search_state.training_function,
                search_alg=search_state.search_alg,
                time_budget_s=min(budget_left, self._state.train_time_limit),
                verbose=max(self.verbose - 1, 0),
                use_ray=False)
            time_used = time.time() - start_run_time
            better = False
            if analysis.trials:
                result = analysis.trials[-1].last_result
                search_state.update(result,
                                    time_used=time_used,
                                    save_model_history=self._save_model_history)
                if self._estimator_index is None:
                    eci_base = search_state.init_eci
                    self._eci.append(search_state.estimated_cost4improvement)
                    for e in self.estimator_list[1:]:
                        self._eci.append(self._search_states[e].init_eci
                                         / eci_base * self._eci[0])
                    self._estimator_index = 0
                if result['wall_clock_time'] is not None:
                    self._state.time_from_start = result['wall_clock_time']
                # logger.info(f"{self._search_states[estimator].sample_size}, {data_size}")
                if search_state.sample_size == self._state.data_size:
                    self._iter_per_learner[estimator] += 1
                    if not self._fullsize_reached:
                        self._fullsize_reached = True
                if search_state.best_loss < self._state.best_loss:
                    best_config_sig = estimator + search_state.get_hist_config_sig(
                        self.data_size_full,
                        search_state.best_config)
                    self._state.best_loss = search_state.best_loss
                    self._best_estimator = estimator
                    est_retrain_time = search_state.est_retrain_time(
                        self.data_size_full) if (
                            best_config_sig not in self._retrained_config) else 0
                    self._config_history[self._track_iter] = (
                        estimator,
                        search_state.best_config,
                        self._state.time_from_start)
                    if self._save_model_history:
                        self._model_history[
                            self._track_iter] = search_state.trained_estimator
                    elif self._trained_estimator:
                        del self._trained_estimator
                        self._trained_estimator = None
                    self._trained_estimator = search_state.trained_estimator
                    self._best_iteration = self._track_iter
                    self._time_taken_best_iter = self._state.time_from_start
                    better = True
                    next_trial_time = search_state.time2eval_best
                if better or self._log_type == 'all':
                    if self._training_log:
                        self._training_log.append(
                            self._iter_per_learner[estimator],
                            search_state.train_loss,
                            search_state.trial_time,
                            self._state.time_from_start,
                            search_state.val_loss,
                            search_state.config,
                            search_state.best_loss,
                            search_state.best_config,
                            estimator,
                            search_state.sample_size)
                    if mlflow is not None and mlflow.active_run():
                        with mlflow.start_run(nested=True):
                            mlflow.log_metric('iter_counter',
                                              self._iter_per_learner[estimator])
                            mlflow.log_param('train_loss',
                                             search_state.train_loss)
                            mlflow.log_metric('trial_time',
                                              search_state.trial_time)
                            mlflow.log_metric('wall_clock_time',
                                              self._state.time_from_start)
                            mlflow.log_metric('validation_loss',
                                              search_state.val_loss)
                            mlflow.log_param('config',
                                             search_state.config)
                            mlflow.log_param('learner',
                                             estimator)
                            mlflow.log_param('sample_size',
                                             search_state.sample_size)
                            mlflow.log_metric('best_validation_loss',
                                              search_state.best_loss)
                            mlflow.log_param('best_config',
                                             search_state.best_config)
                            mlflow.log_param('best_learner',
                                             self._best_estimator)
                logger.info(
                    " at {:.1f}s,\tbest {}'s error={:.4f},\tbest {}'s error={:.4f}".format(
                        self._state.time_from_start,
                        estimator,
                        search_state.best_loss,
                        self._best_estimator,
                        self._state.best_loss))
                if all(state.search_alg and state.search_alg.searcher.is_ls_ever_converged
                       for state in self._search_states.values()) and (
                           self._state.time_from_start
                           > self._warn_threshold * self._time_taken_best_iter):
                    logger.warn("All estimator hyperparameters local search has converged at least once, "
                                f"and the total search time exceeds {self._warn_threshold} times the time taken "
                                "to find the best model.")
                    self._warn_threshold *= 10
            else:
                logger.info(f"no enough budget for learner {estimator}")
                if self._estimator_index is not None:
                    self._active_estimators.remove(estimator)
                    self._estimator_index -= 1
            if self._retrain_in_budget and best_config_sig and est_retrain_time \
               and not better and self._search_states[
                   self._best_estimator].sample_size == self._state.data_size and (
                       est_retrain_time
                       <= self._state.time_budget - self._state.time_from_start
                       <= est_retrain_time + next_trial_time):
                self._trained_estimator, \
                    retrain_time = self._state._train_with_config(
                        self._best_estimator,
                        self._search_states[self._best_estimator].best_config,
                        self.data_size_full)
                logger.info("retrain {} for {:.1f}s".format(
                    self._best_estimator, retrain_time))
                self._retrained_config[best_config_sig] = retrain_time
                est_retrain_time = 0
            self._state.time_from_start = time.time() - self._start_time_flag
            if (self._state.time_from_start >= self._state.time_budget
                    or not self._active_estimators):
                break
            if self._ensemble and self._best_estimator:
                time_left = self._state.time_budget - self._state.time_from_start
                time_ensemble = self._search_states[
                    self._best_estimator].time2eval_best
                if time_left < time_ensemble < 2 * time_left:
                    break

    def _search(self):
        # initialize the search_states
        self._eci = []
        self._state.best_loss = float('+inf')
        self._state.time_from_start = 0
        self._estimator_index = None
        self._best_iteration = 0
        self._time_taken_best_iter = 0
        self._model_history = {}
        self._config_history = {}
        self._max_iter_per_learner = 1000000  # TODO
        self._iter_per_learner = dict([(e, 0) for e in self.estimator_list])
        self._fullsize_reached = False
        self._trained_estimator = None
        self._best_estimator = None
        self._retrained_config = {}
        self._warn_threshold = 10

        if self._n_concurrent_trials == 1:
            self._search_sequential()
        else:
            self._search_parallel()
        # Add a checkpoint for the current best config to the log.
        if self._training_log:
            self._training_log.checkpoint()
        if self._best_estimator:
            self._selected = self._search_states[self._best_estimator]
            self.modelcount = sum(
                search_state.total_iter
                for search_state in self._search_states.values())
            if self._trained_estimator:
                logger.info(f'selected model: {self._trained_estimator.model}')
            if self._ensemble:
                search_states = list(x for x in self._search_states.items()
                                     if x[1].trained_estimator)
                search_states.sort(key=lambda x: x[1].best_loss)
                estimators = [(x[0], x[1].trained_estimator)
                              for x in search_states[:2]]
                estimators += [
                    (x[0], x[1].trained_estimator) for x in search_states[2:]
                    if x[1].best_loss < 4 * self._selected.best_loss]
                logger.info(estimators)
                if len(estimators) <= 1:
                    return
                if self._state.task != "regression":
                    from sklearn.ensemble import StackingClassifier as Stacker
                    for e in estimators:
                        e[1]._estimator_type = 'classifier'
                else:
                    from sklearn.ensemble import StackingRegressor as Stacker
                best_m = self._trained_estimator
                stacker = Stacker(estimators, best_m, n_jobs=self._state.n_jobs,
                                  passthrough=True)
                if self._sample_weight_full is not None:
                    self._state.fit_kwargs[
                        'sample_weight'] = self._sample_weight_full
                stacker.fit(self._X_train_all, self._y_train_all,
                            **self._state.fit_kwargs)
                logger.info(f'ensemble: {stacker}')
                self._trained_estimator = stacker
                self._trained_estimator.model = stacker
            elif self._retrain_final:
                # reset time budget for retraining
                self._state.time_from_start -= self._state.time_budget
                if (self._state.time_budget - self._state.time_from_start
                    > self._selected.est_retrain_time(self.data_size_full)) \
                   and self._selected.best_config_sample_size == self._state.data_size:
                    self._trained_estimator, \
                        retrain_time = self._state._train_with_config(
                            self._best_estimator,
                            self._search_states[self._best_estimator].best_config,
                            self.data_size_full)
                    logger.info("retrain {} for {:.1f}s".format(
                        self._best_estimator, retrain_time))
                    if self._trained_estimator:
                        logger.info(
                            f'retrained model: {self._trained_estimator.model}')
                else:
                    logger.info(
                        "not retraining because the time budget is too small.")
        else:
            self._selected = self._trained_estimator = None
            self.modelcount = 0
        if self.model and mlflow is not None and mlflow.active_run():
            mlflow.sklearn.log_model(self.model, 'best_model')

    def __del__(self):
        if hasattr(self, '_trained_estimator') and self._trained_estimator \
                and hasattr(self._trained_estimator, 'cleanup'):
            self._trained_estimator.cleanup()
            del self._trained_estimator

    def _select_estimator(self, estimator_list):
        if self._learner_selector == 'roundrobin':
            self._estimator_index += 1
            if self._estimator_index == len(estimator_list):
                self._estimator_index = 0
            return estimator_list[self._estimator_index]
        min_estimated_cost, selected = np.Inf, None
        inv = []
        untried_exists = False
        for i, estimator in enumerate(estimator_list):
            if estimator in self._search_states and (
                self._search_states[estimator].sample_size
            ):  # sample_size=None meaning no result
                search_state = self._search_states[estimator]
                if (self._search_states[estimator].time2eval_best
                    > self._state.time_budget - self._state.time_from_start
                    or self._iter_per_learner[estimator]
                        >= self._max_iter_per_learner):
                    inv.append(0)
                    continue
                estimated_cost = search_state.estimated_cost4improvement
                if search_state.sample_size < self._state.data_size:
                    estimated_cost = min(
                        estimated_cost,
                        search_state.time2eval_best * min(
                            SAMPLE_MULTIPLY_FACTOR,
                            self._state.data_size / search_state.sample_size))
                gap = search_state.best_loss - self._state.best_loss
                if gap > 0 and not self._ensemble:
                    delta_loss = (search_state.best_loss_old
                                  - search_state.best_loss) or search_state.best_loss
                    delta_time = (search_state.total_time_used
                                  - search_state.time_best_found_old) or 1e-10
                    speed = delta_loss / delta_time
                    if speed:
                        estimated_cost = max(2 * gap / speed, estimated_cost)
                if estimated_cost == 0:
                    estimated_cost = 1e-10
                inv.append(1 / estimated_cost)
            else:
                estimated_cost = self._eci[i]
                inv.append(0)
                untried_exists = True
            if estimated_cost < min_estimated_cost:
                min_estimated_cost = estimated_cost
                selected = estimator
        if untried_exists or not selected:
            state = self._search_states.get(selected)
            if not (state and state.sample_size):
                return selected
        s = sum(inv)
        p = self._random.rand()
        q = 0
        for i in range(len(inv)):
            if inv[i]:
                q += inv[i] / s
                if p < q:
                    return estimator_list[i]
