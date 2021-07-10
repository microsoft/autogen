'''!
 * Copyright (c) 2020-2021 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License.
'''

import numpy as np
import xgboost as xgb
import time
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.ensemble import ExtraTreesRegressor, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from lightgbm import LGBMClassifier, LGBMRegressor
from scipy.sparse import issparse
import pandas as pd
from . import tune

import logging
logger = logging.getLogger(__name__)


class BaseEstimator:
    '''The abstract class for all learners

    Typical example:
        XGBoostEstimator: for regression
        XGBoostSklearnEstimator: for classification
        LGBMEstimator, RandomForestEstimator, LRL1Classifier, LRL2Classifier:
            for both regression and classification
    '''

    def __init__(self, task='binary:logistic', **params):
        '''Constructor

        Args:
            task: A string of the task type, one of
                'binary:logistic', 'multi:softmax', 'regression'
            n_jobs: An integer of the number of parallel threads
            params: A dictionary of the hyperparameter names and values
        '''
        self.params = params
        self.estimator_class = self._model = None
        self._task = task
        if '_estimator_type' in params:
            self._estimator_type = params['_estimator_type']
            del self.params['_estimator_type']
        else:
            self._estimator_type = "regressor" if task == 'regression' \
                else "classifier"

    def get_params(self, deep=False):
        params = self.params.copy()
        params["task"] = self._task
        if hasattr(self, '_estimator_type'):
            params['_estimator_type'] = self._estimator_type
        return params

    @property
    def classes_(self):
        return self._model.classes_

    @property
    def n_features_in_(self):
        return self.model.n_features_in_

    @property
    def model(self):
        '''Trained model after fit() is called, or None before fit() is called
        '''
        return self._model

    @property
    def estimator(self):
        '''Trained model after fit() is called, or None before fit() is called
        '''
        return self._model

    def _preprocess(self, X):
        return X

    def _fit(self, X_train, y_train, **kwargs):

        current_time = time.time()
        X_train = self._preprocess(X_train)
        model = self.estimator_class(**self.params)
        model.fit(X_train, y_train, **kwargs)
        train_time = time.time() - current_time
        self._model = model
        return train_time

    def fit(self, X_train, y_train, budget=None, **kwargs):
        '''Train the model from given training data

        Args:
            X_train: A numpy array of training data in shape n*m
            y_train: A numpy array of labels in shape n*1
            budget: A float of the time budget in seconds

        Returns:
            train_time: A float of the training time in seconds
        '''
        return self._fit(X_train, y_train, **kwargs)

    def predict(self, X_test):
        '''Predict label from features

        Args:
            X_test: A numpy array of featurized instances, shape n*m

        Returns:
            A numpy array of shape n*1.
            Each element is the label for a instance
        '''
        if self._model is not None:
            X_test = self._preprocess(X_test)
            return self._model.predict(X_test)
        else:
            return np.ones(X_test.shape[0])

    def predict_proba(self, X_test):
        '''Predict the probability of each class from features

        Only works for classification problems

        Args:
            model: An object of trained model with method predict_proba()
            X_test: A numpy array of featurized instances, shape n*m

        Returns:
            A numpy array of shape n*c. c is the # classes
            Each element at (i,j) is the probability for instance i to be in
                class j
        '''
        if 'regression' in self._task:
            raise ValueError('Regression tasks do not support predict_prob')
        else:
            X_test = self._preprocess(X_test)
            return self._model.predict_proba(X_test)

    def cleanup(self):
        pass

    @classmethod
    def search_space(cls, **params):
        '''[required method] search space

        Returns:
            A dictionary of the search space.
            Each key is the name of a hyperparameter, and value is a dict with
                its domain and init_value (optional), cat_hp_cost (optional)
                e.g.,
                {'domain': tune.randint(lower=1, upper=10), 'init_value': 1}
        '''
        return {}

    @classmethod
    def size(cls, config: dict) -> float:
        '''[optional method] memory size of the estimator in bytes

        Args:
            config - the dict of the hyperparameter config

        Returns:
            A float of the memory size required by the estimator to train the
            given config
        '''
        return 1.0

    @classmethod
    def cost_relative2lgbm(cls) -> float:
        '''[optional method] relative cost compared to lightgbm'''
        return 1.0

    @classmethod
    def init(cls):
        '''[optional method] initialize the class'''
        pass


class SKLearnEstimator(BaseEstimator):

    def __init__(self, task='binary:logistic', **params):
        super().__init__(task, **params)

    def _preprocess(self, X):
        if isinstance(X, pd.DataFrame):
            X = X.copy()
            cat_columns = X.select_dtypes(include=['category']).columns
            X[cat_columns] = X[cat_columns].apply(lambda x: x.cat.codes)
        return X


class LGBMEstimator(BaseEstimator):

    @classmethod
    def search_space(cls, data_size, **params):
        upper = min(32768, int(data_size))
        return {
            'n_estimators': {
                'domain': tune.qloguniform(lower=4, upper=upper, q=1),
                'init_value': 4,
                'low_cost_init_value': 4,
            },
            'num_leaves': {
                'domain': tune.qloguniform(lower=4, upper=upper, q=1),
                'init_value': 4,
                'low_cost_init_value': 4,
            },
            'min_child_samples': {
                'domain': tune.qloguniform(lower=2, upper=2**7, q=1),
                'init_value': 20,
            },
            'learning_rate': {
                'domain': tune.loguniform(lower=1 / 1024, upper=1.0),
                'init_value': 0.1,
            },
            'subsample': {
                'domain': tune.uniform(lower=0.1, upper=1.0),
                'init_value': 1.0,
            },
            'log_max_bin': {
                'domain': tune.qloguniform(lower=3, upper=10, q=1),
                'init_value': 8,
            },
            'colsample_bytree': {
                'domain': tune.uniform(lower=0.01, upper=1.0),
                'init_value': 1.0,
            },
            'reg_alpha': {
                'domain': tune.loguniform(lower=1 / 1024, upper=1024),
                'init_value': 1 / 1024,
            },
            'reg_lambda': {
                'domain': tune.loguniform(lower=1 / 1024, upper=1024),
                'init_value': 1.0,
            },
        }

    @classmethod
    def size(cls, config):
        num_leaves = int(round(config.get('num_leaves') or config['max_leaves']))
        n_estimators = int(round(config['n_estimators']))
        return (num_leaves * 3 + (num_leaves - 1) * 4 + 1.0) * n_estimators * 8

    def __init__(self, task='binary:logistic', log_max_bin=8, **params):
        super().__init__(task, **params)
        # Default: ‘regression’ for LGBMRegressor,
        # ‘binary’ or ‘multiclass’ for LGBMClassifier
        if 'regression' in task:
            objective = 'regression'
        elif 'binary' in task:
            objective = 'binary'
        elif 'multi' in task:
            objective = 'multiclass'
        else:
            objective = 'regression'
        if "n_estimators" in self.params:
            self.params["n_estimators"] = int(round(self.params["n_estimators"]))
        if "num_leaves" in self.params:
            self.params["num_leaves"] = int(round(self.params["num_leaves"]))
        if "min_child_samples" in self.params:
            self.params["min_child_samples"] = int(round(self.params["min_child_samples"]))
        if "objective" not in self.params:
            self.params["objective"] = objective
        if "max_bin" not in self.params:
            self.params['max_bin'] = 1 << int(round(log_max_bin)) - 1
        if 'regression' in task:
            self.estimator_class = LGBMRegressor
        else:
            self.estimator_class = LGBMClassifier
        self._time_per_iter = None
        self._train_size = 0

    def _preprocess(self, X):
        if not isinstance(X, pd.DataFrame) and issparse(X) and np.issubdtype(
                X.dtype, np.integer):
            X = X.astype(float)
        return X

    def fit(self, X_train, y_train, budget=None, **kwargs):
        start_time = time.time()
        n_iter = self.params["n_estimators"]
        if (not self._time_per_iter or abs(
                self._train_size - X_train.shape[0]) > 4) and budget is not None:
            self.params["n_estimators"] = 1
            self._t1 = self._fit(X_train, y_train, **kwargs)
            if self._t1 >= budget:
                self.params["n_estimators"] = n_iter
                return self._t1
            self.params["n_estimators"] = 4
            self._t2 = self._fit(X_train, y_train, **kwargs)
            self._time_per_iter = (self._t2 - self._t1) / (
                self.params["n_estimators"] - 1) if self._t2 > self._t1 \
                else self._t1 if self._t1 else 0.001
            self._train_size = X_train.shape[0]
            if self._t1 + self._t2 >= budget or n_iter == self.params[
                    "n_estimators"]:
                self.params["n_estimators"] = n_iter
                return time.time() - start_time
        if budget is not None:
            self.params["n_estimators"] = min(n_iter, int(
                (budget - time.time() + start_time - self._t1)
                / self._time_per_iter + 1))
        if self.params["n_estimators"] > 0:
            self._fit(X_train, y_train, **kwargs)
        self.params["n_estimators"] = n_iter
        train_time = time.time() - start_time
        return train_time


class XGBoostEstimator(SKLearnEstimator):
    ''' not using sklearn API, used for regression '''

    @classmethod
    def search_space(cls, data_size, **params):
        upper = min(32768, int(data_size))
        return {
            'n_estimators': {
                'domain': tune.qloguniform(lower=4, upper=upper, q=1),
                'init_value': 4,
                'low_cost_init_value': 4,
            },
            'max_leaves': {
                'domain': tune.qloguniform(lower=4, upper=upper, q=1),
                'init_value': 4,
                'low_cost_init_value': 4,
            },
            'min_child_weight': {
                'domain': tune.loguniform(lower=0.001, upper=128),
                'init_value': 1,
            },
            'learning_rate': {
                'domain': tune.loguniform(lower=1 / 1024, upper=1.0),
                'init_value': 0.1,
            },
            'subsample': {
                'domain': tune.uniform(lower=0.1, upper=1.0),
                'init_value': 1.0,
            },
            'colsample_bylevel': {
                'domain': tune.uniform(lower=0.01, upper=1.0),
                'init_value': 1.0,
            },
            'colsample_bytree': {
                'domain': tune.uniform(lower=0.01, upper=1.0),
                'init_value': 1.0,
            },
            'reg_alpha': {
                'domain': tune.loguniform(lower=1 / 1024, upper=1024),
                'init_value': 1 / 1024,
            },
            'reg_lambda': {
                'domain': tune.loguniform(lower=1 / 1024, upper=1024),
                'init_value': 1.0,
            },
        }

    @classmethod
    def size(cls, config):
        return LGBMEstimator.size(config)

    @classmethod
    def cost_relative2lgbm(cls):
        return 1.6

    def __init__(
        self, task='regression', all_thread=False, n_jobs=1,
        n_estimators=4, max_leaves=4, subsample=1.0, min_child_weight=1,
        learning_rate=0.1, reg_lambda=1.0, reg_alpha=0.0, colsample_bylevel=1.0,
        colsample_bytree=1.0, tree_method='auto', **params
    ):
        super().__init__(task, **params)
        self._n_estimators = int(round(n_estimators))
        self.params.update({
            'max_leaves': int(round(max_leaves)),
            'max_depth': params.get('max_depth', 0),
            'grow_policy': params.get("grow_policy", 'lossguide'),
            'tree_method': tree_method,
            'verbosity': params.get('verbosity', 0),
            'nthread': n_jobs,
            'learning_rate': float(learning_rate),
            'subsample': float(subsample),
            'reg_alpha': float(reg_alpha),
            'reg_lambda': float(reg_lambda),
            'min_child_weight': float(min_child_weight),
            'booster': params.get('booster', 'gbtree'),
            'colsample_bylevel': float(colsample_bylevel),
            'colsample_bytree': float(colsample_bytree),
            'objective': params.get("objective")
        })
        if all_thread:
            del self.params['nthread']

    def get_params(self, deep=False):
        params = super().get_params()
        params["n_jobs"] = params['nthread']
        return params

    def fit(self, X_train, y_train, budget=None, **kwargs):
        start_time = time.time()
        if not issparse(X_train):
            self.params['tree_method'] = 'hist'
            X_train = self._preprocess(X_train)
        if 'sample_weight' in kwargs:
            dtrain = xgb.DMatrix(X_train, label=y_train, weight=kwargs[
                'sample_weight'])
        else:
            dtrain = xgb.DMatrix(X_train, label=y_train)

        objective = self.params.get('objective')
        if isinstance(objective, str):
            obj = None
        else:
            obj = objective
            if 'objective' in self.params:
                del self.params['objective']
        self._model = xgb.train(self.params, dtrain, self._n_estimators,
                                obj=obj)
        self.params['objective'] = objective
        del dtrain
        train_time = time.time() - start_time
        return train_time

    def predict(self, X_test):
        if not issparse(X_test):
            X_test = self._preprocess(X_test)
        dtest = xgb.DMatrix(X_test)
        return super().predict(dtest)


class XGBoostSklearnEstimator(SKLearnEstimator, LGBMEstimator):
    ''' using sklearn API, used for classification '''

    @classmethod
    def search_space(cls, data_size, **params):
        return XGBoostEstimator.search_space(data_size)

    @classmethod
    def cost_relative2lgbm(cls):
        return XGBoostEstimator.cost_relative2lgbm()

    def __init__(
        self, task='binary:logistic', n_jobs=1,
        n_estimators=4, max_leaves=4, subsample=1.0,
        min_child_weight=1, learning_rate=0.1, reg_lambda=1.0, reg_alpha=0.0,
        colsample_bylevel=1.0, colsample_bytree=1.0, tree_method='hist',
        **params
    ):
        super().__init__(task, **params)
        del self.params['objective']
        del self.params['max_bin']
        self.params.update({
            "n_estimators": int(round(n_estimators)),
            'max_leaves': int(round(max_leaves)),
            'max_depth': 0,
            'grow_policy': params.get("grow_policy", 'lossguide'),
            'tree_method': tree_method,
            'verbosity': 0,
            'n_jobs': n_jobs,
            'learning_rate': float(learning_rate),
            'subsample': float(subsample),
            'reg_alpha': float(reg_alpha),
            'reg_lambda': float(reg_lambda),
            'min_child_weight': float(min_child_weight),
            'booster': params.get('booster', 'gbtree'),
            'colsample_bylevel': float(colsample_bylevel),
            'colsample_bytree': float(colsample_bytree),
            'use_label_encoder': params.get('use_label_encoder', False),
        })

        if 'regression' in task:
            self.estimator_class = xgb.XGBRegressor
        else:
            self.estimator_class = xgb.XGBClassifier
        self._time_per_iter = None
        self._train_size = 0

    def fit(self, X_train, y_train, budget=None, **kwargs):
        if issparse(X_train):
            self.params['tree_method'] = 'auto'
        return super().fit(X_train, y_train, budget, **kwargs)


class RandomForestEstimator(SKLearnEstimator, LGBMEstimator):

    @classmethod
    def search_space(cls, data_size, task, **params):
        upper = min(2048, int(data_size))
        space = {
            'n_estimators': {
                'domain': tune.qloguniform(lower=4, upper=upper, q=1),
                'init_value': 4,
                'low_cost_init_value': 4,
            },
            'max_features': {
                'domain': tune.loguniform(lower=0.1, upper=1.0),
                'init_value': 1.0,
            },
        }
        if task != 'regression':
            space['criterion'] = {
                'domain': tune.choice(['gini', 'entropy']),
                # 'init_value': 'gini',
            }
        return space

    @classmethod
    def size(cls, config):
        return 1.0

    @classmethod
    def cost_relative2lgbm(cls):
        return 2.0

    def __init__(
        self, task='binary:logistic', n_jobs=1,
        n_estimators=4, max_features=1.0, criterion='gini', **params
    ):
        super().__init__(task, **params)
        del self.params['objective']
        del self.params['max_bin']
        self.params.update({
            "n_estimators": int(round(n_estimators)),
            "n_jobs": n_jobs,
            'max_features': float(max_features),
        })
        if 'regression' in task:
            self.estimator_class = RandomForestRegressor
        else:
            self.estimator_class = RandomForestClassifier
            self.params['criterion'] = criterion

    def get_params(self, deep=False):
        params = super().get_params()
        return params


class ExtraTreeEstimator(RandomForestEstimator):

    @classmethod
    def cost_relative2lgbm(cls):
        return 1.9

    def __init__(self, task='binary:logistic', **params):
        super().__init__(task, **params)
        if 'regression' in task:
            self.estimator_class = ExtraTreesRegressor
        else:
            self.estimator_class = ExtraTreesClassifier


class LRL1Classifier(SKLearnEstimator):

    @classmethod
    def search_space(cls, **params):
        return {
            'C': {
                'domain': tune.loguniform(lower=0.03125, upper=32768.0),
                'init_value': 1.0,
            },
        }

    @classmethod
    def cost_relative2lgbm(cls):
        return 160

    def __init__(
        self, task='binary:logistic', n_jobs=1, tol=0.0001, C=1.0,
        **params
    ):
        super().__init__(task, **params)
        self.params.update({
            'penalty': params.get("penalty", 'l1'),
            'tol': float(tol),
            'C': float(C),
            'solver': params.get("solver", 'saga'),
            'n_jobs': n_jobs,
        })
        if 'regression' in task:
            self.estimator_class = None
            raise NotImplementedError('LR does not support regression task')
        else:
            self.estimator_class = LogisticRegression


class LRL2Classifier(SKLearnEstimator):

    @classmethod
    def search_space(cls, **params):
        return LRL1Classifier.search_space(**params)

    @classmethod
    def cost_relative2lgbm(cls):
        return 25

    def __init__(
        self, task='binary:logistic', n_jobs=1, tol=0.0001, C=1.0,
        **params
    ):
        super().__init__(task, **params)
        self.params.update({
            'penalty': params.get("penalty", 'l2'),
            'tol': float(tol),
            'C': float(C),
            'solver': params.get("solver", 'lbfgs'),
            'n_jobs': n_jobs,
        })
        if 'regression' in task:
            self.estimator_class = None
            raise NotImplementedError('LR does not support regression task')
        else:
            self.estimator_class = LogisticRegression


class CatBoostEstimator(BaseEstimator):

    _time_per_iter = None
    _train_size = 0

    @classmethod
    def search_space(cls, data_size, **params):
        upper = max(min(round(1500000 / data_size), 150), 11)
        return {
            'early_stopping_rounds': {
                'domain': tune.qloguniform(lower=10, upper=upper, q=1),
                'init_value': 10,
                'low_cost_init_value': 10,
            },
            'learning_rate': {
                'domain': tune.loguniform(lower=.005, upper=.2),
                'init_value': 0.1,
            },
        }

    @classmethod
    def size(cls, config):
        n_estimators = 8192
        max_leaves = 64
        return (max_leaves * 3 + (max_leaves - 1) * 4 + 1.0) * n_estimators * 8

    @classmethod
    def cost_relative2lgbm(cls):
        return 15

    @classmethod
    def init(cls):
        CatBoostEstimator._time_per_iter = None
        CatBoostEstimator._train_size = 0

    def __init__(
        self, task='binary:logistic', n_jobs=1,
        n_estimators=8192, learning_rate=0.1, early_stopping_rounds=4, **params
    ):
        super().__init__(task, **params)
        self.params.update({
            "early_stopping_rounds": int(round(early_stopping_rounds)),
            "n_estimators": n_estimators,
            'learning_rate': learning_rate,
            'thread_count': n_jobs,
            'verbose': params.get('verbose', False),
            'random_seed': params.get("random_seed", 10242048),
        })
        if 'regression' in task:
            from catboost import CatBoostRegressor
            self.estimator_class = CatBoostRegressor
        else:
            from catboost import CatBoostClassifier
            self.estimator_class = CatBoostClassifier

    def get_params(self, deep=False):
        params = super().get_params()
        params['n_jobs'] = params['thread_count']
        return params

    def fit(self, X_train, y_train, budget=None, **kwargs):
        start_time = time.time()
        n_iter = self.params["n_estimators"]
        if isinstance(X_train, pd.DataFrame):
            cat_features = list(X_train.select_dtypes(
                include='category').columns)
        else:
            cat_features = []
        from catboost import CatBoostError
        try:
            if (not CatBoostEstimator._time_per_iter or abs(
                    CatBoostEstimator._train_size - len(y_train)) > 4) and budget:
                # measure the time per iteration
                self.params["n_estimators"] = 1
                CatBoostEstimator._smallmodel = self.estimator_class(**self.params)
                CatBoostEstimator._smallmodel.fit(
                    X_train, y_train, cat_features=cat_features, **kwargs)
                CatBoostEstimator._t1 = time.time() - start_time
                if CatBoostEstimator._t1 >= budget:
                    self.params["n_estimators"] = n_iter
                    self._model = CatBoostEstimator._smallmodel
                    return CatBoostEstimator._t1
                self.params["n_estimators"] = 4
                CatBoostEstimator._smallmodel = self.estimator_class(**self.params)
                CatBoostEstimator._smallmodel.fit(
                    X_train, y_train, cat_features=cat_features, **kwargs)
                CatBoostEstimator._time_per_iter = (
                    time.time() - start_time - CatBoostEstimator._t1) / (
                        self.params["n_estimators"] - 1)
                if CatBoostEstimator._time_per_iter <= 0:
                    CatBoostEstimator._time_per_iter = CatBoostEstimator._t1
                CatBoostEstimator._train_size = len(y_train)
                if time.time() - start_time >= budget or n_iter == self.params[
                        "n_estimators"]:
                    self.params["n_estimators"] = n_iter
                    self._model = CatBoostEstimator._smallmodel
                    return time.time() - start_time
            if budget:
                train_times = 1
                self.params["n_estimators"] = min(n_iter, int(
                    (budget - time.time() + start_time - CatBoostEstimator._t1)
                    / train_times / CatBoostEstimator._time_per_iter + 1))
                self._model = CatBoostEstimator._smallmodel
            if self.params["n_estimators"] > 0:
                n = max(int(len(y_train) * 0.9), len(y_train) - 1000)
                X_tr, y_tr = X_train[:n], y_train[:n]
                if 'sample_weight' in kwargs:
                    weight = kwargs['sample_weight']
                    if weight is not None:
                        kwargs['sample_weight'] = weight[:n]
                else:
                    weight = None
                from catboost import Pool
                model = self.estimator_class(**self.params)
                model.fit(
                    X_tr, y_tr, cat_features=cat_features,
                    eval_set=Pool(
                        data=X_train[n:], label=y_train[n:],
                        cat_features=cat_features),
                    **kwargs)   # model.get_best_iteration()
                if weight is not None:
                    kwargs['sample_weight'] = weight
                self._model = model
        except CatBoostError:
            self._model = None
        self.params["n_estimators"] = n_iter
        train_time = time.time() - start_time
        return train_time


class KNeighborsEstimator(BaseEstimator):

    @classmethod
    def search_space(cls, data_size, **params):
        upper = min(512, int(data_size / 2))
        return {
            'n_neighbors': {
                'domain': tune.qloguniform(lower=1, upper=upper, q=1),
                'init_value': 5,
                'low_cost_init_value': 1,
            },
        }

    @classmethod
    def cost_relative2lgbm(cls):
        return 30

    def __init__(
        self, task='binary:logistic', n_jobs=1, n_neighbors=5, **params
    ):
        super().__init__(task, **params)
        self.params.update({
            'n_neighbors': int(round(n_neighbors)),
            'weights': params.get('weights', 'distance'),
            'n_jobs': n_jobs,
        })
        if 'regression' in task:
            from sklearn.neighbors import KNeighborsRegressor
            self.estimator_class = KNeighborsRegressor
        else:
            from sklearn.neighbors import KNeighborsClassifier
            self.estimator_class = KNeighborsClassifier

    def _preprocess(self, X):
        if isinstance(X, pd.DataFrame):
            cat_columns = X.select_dtypes(['category']).columns
            if X.shape[1] == len(cat_columns):
                raise ValueError(
                    "kneighbor requires at least one numeric feature")
            X = X.drop(cat_columns, axis=1)
        return X
