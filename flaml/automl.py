# !
#  * Copyright (c) FLAML authors. All rights reserved.
#  * Licensed under the MIT License. See LICENSE file in the
#  * project root for license information.
import time
import os
from typing import Callable, Optional, List, Union
from functools import partial
import numpy as np
from scipy.sparse import issparse
from sklearn.model_selection import (
    train_test_split,
    RepeatedStratifiedKFold,
    RepeatedKFold,
    GroupKFold,
    TimeSeriesSplit,
    GroupShuffleSplit,
)
from sklearn.utils import shuffle
from sklearn.base import BaseEstimator
import pandas as pd
import logging
import json
from .ml import (
    compute_estimator,
    train_estimator,
    get_estimator_class,
    get_classification_objective,
)
from .config import (
    MIN_SAMPLE_TRAIN,
    MEM_THRES,
    RANDOM_SEED,
    SMALL_LARGE_THRES,
    CV_HOLDOUT_THRESHOLD,
    SPLIT_RATIO,
    N_SPLITS,
    SAMPLE_MULTIPLY_FACTOR,
)
from .data import (
    concat,
    CLASSIFICATION,
    TOKENCLASSIFICATION,
    TS_FORECAST,
    FORECAST,
    REGRESSION,
    _is_nlp_task,
    NLG_TASKS,
)
from . import tune
from .training_log import training_log_reader, training_log_writer

logger = logging.getLogger(__name__)
logger_formatter = logging.Formatter(
    "[%(name)s: %(asctime)s] {%(lineno)d} %(levelname)s - %(message)s", "%m-%d %H:%M:%S"
)

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
        return max(
            self.time_best_found - self.time_best_found_old,
            self.total_time_used - self.time_best_found,
        )

    def __init__(
        self, learner_class, data_size, task, starting_point=None, period=None
    ):
        self.init_eci = learner_class.cost_relative2lgbm()
        self._search_space_domain = {}
        self.init_config = {}
        self.low_cost_partial_config = {}
        self.cat_hp_cost = {}
        self.data_size = data_size
        self.ls_ever_converged = False
        self.learner_class = learner_class
        if task == TS_FORECAST:
            search_space = learner_class.search_space(
                data_size=data_size, task=task, pred_horizon=period
            )
        else:
            search_space = learner_class.search_space(data_size=data_size, task=task)
        for name, space in search_space.items():
            assert (
                "domain" in space
            ), f"{name}'s domain is missing in the search space spec {space}"
            self._search_space_domain[name] = space["domain"]
            if "init_value" in space:
                self.init_config[name] = space["init_value"]
            if "low_cost_init_value" in space:
                self.low_cost_partial_config[name] = space["low_cost_init_value"]
            if "cat_hp_cost" in space:
                self.cat_hp_cost[name] = space["cat_hp_cost"]
            # if a starting point is provided, set the init config to be
            # the starting point provided
            if (
                isinstance(starting_point, dict)
                and starting_point.get(name) is not None
            ):
                self.init_config[name] = starting_point[name]

        if isinstance(starting_point, list):
            self.init_config = starting_point
        self._hp_names = list(self._search_space_domain.keys())
        self.search_alg = None
        self.best_config = None
        self.best_loss = self.best_loss_old = np.inf
        self.total_time_used = 0
        self.total_iter = 0
        self.base_eci = None
        self.time_best_found = self.time_best_found_old = 0
        self.time2eval_best = 0
        self.time2eval_best_old = 0
        self.trained_estimator = None
        self.sample_size = None
        self.trial_time = 0

    def update(self, result, time_used):
        if result:
            config = result["config"]
            if config and "FLAML_sample_size" in config:
                self.sample_size = config["FLAML_sample_size"]
            else:
                self.sample_size = self.data_size[0]
            obj = result["val_loss"]
            metric_for_logging = result["metric_for_logging"]
            time2eval = result["time_total_s"]
            trained_estimator = result["trained_estimator"]
            del result["trained_estimator"]  # free up RAM
            n_iter = (
                trained_estimator
                and hasattr(trained_estimator, "ITER_HP")
                and trained_estimator.params[trained_estimator.ITER_HP]
            )
            if n_iter:
                config[trained_estimator.ITER_HP] = n_iter
        else:
            obj, time2eval, trained_estimator = np.inf, 0.0, None
            metric_for_logging = config = None
        self.trial_time = time2eval
        self.total_time_used += time_used
        self.total_iter += 1

        if self.base_eci is None:
            self.base_eci = time_used
        if (obj is not None) and (self.best_loss is None or obj < self.best_loss):
            self.best_loss_old = self.best_loss if self.best_loss < np.inf else 2 * obj
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
            if (
                self.trained_estimator
                and trained_estimator
                and self.trained_estimator != trained_estimator
            ):
                self.trained_estimator.cleanup()
            if trained_estimator:
                self.trained_estimator = trained_estimator
        elif trained_estimator:
            trained_estimator.cleanup()
        self.metric_for_logging = metric_for_logging
        self.val_loss, self.config = obj, config

    def get_hist_config_sig(self, sample_size, config):
        config_values = tuple([config[k] for k in self._hp_names])
        config_sig = str(sample_size) + "_" + str(config_values)
        return config_sig

    def est_retrain_time(self, retrain_sample_size):
        assert (
            self.best_config_sample_size is not None
        ), "need to first get best_config_sample_size"
        return self.time2eval_best * retrain_sample_size / self.best_config_sample_size


class AutoMLState:
    def _prepare_sample_train_data(self, sample_size):
        sampled_weight = groups = None
        if sample_size <= self.data_size[0]:
            if isinstance(self.X_train, pd.DataFrame):
                sampled_X_train = self.X_train.iloc[:sample_size]
            else:
                sampled_X_train = self.X_train[:sample_size]
            sampled_y_train = self.y_train[:sample_size]
            weight = self.fit_kwargs.get("sample_weight")
            if weight is not None:
                sampled_weight = weight[:sample_size]
            if self.groups is not None:
                groups = self.groups[:sample_size]
        else:
            sampled_X_train = self.X_train_all
            sampled_y_train = self.y_train_all
            if "sample_weight" in self.fit_kwargs:
                sampled_weight = self.sample_weight_all
            if self.groups is not None:
                groups = self.groups_all
        return sampled_X_train, sampled_y_train, sampled_weight, groups

    def _compute_with_config_base(self, estimator, config_w_resource):
        if "FLAML_sample_size" in config_w_resource:
            sample_size = int(config_w_resource["FLAML_sample_size"])
        else:
            sample_size = self.data_size[0]
        (
            sampled_X_train,
            sampled_y_train,
            sampled_weight,
            groups,
        ) = self._prepare_sample_train_data(sample_size)
        if sampled_weight is not None:
            weight = self.fit_kwargs["sample_weight"]
            self.fit_kwargs["sample_weight"] = sampled_weight
        else:
            weight = None
        if groups is not None:
            self.fit_kwargs["groups"] = groups
        config = config_w_resource.copy()
        if "FLAML_sample_size" in config:
            del config["FLAML_sample_size"]
        budget = (
            None
            if self.time_budget is None
            else self.time_budget - self.time_from_start
            if sample_size == self.data_size[0]
            else (self.time_budget - self.time_from_start)
            / 2
            * sample_size
            / self.data_size[0]
        )

        if _is_nlp_task(self.task):
            self.fit_kwargs["X_val"] = self.X_val
            self.fit_kwargs["y_val"] = self.y_val

        (
            trained_estimator,
            val_loss,
            metric_for_logging,
            _,
            pred_time,
        ) = compute_estimator(
            sampled_X_train,
            sampled_y_train,
            self.X_val,
            self.y_val,
            self.weight_val,
            self.groups_val,
            self.train_time_limit
            if budget is None
            else min(budget, self.train_time_limit),
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
            self.fit_kwargs,
        )
        if self.retrain_final and not self.model_history:
            trained_estimator.cleanup()

        if _is_nlp_task(self.task):
            del self.fit_kwargs["X_val"]
            del self.fit_kwargs["y_val"]

        result = {
            "pred_time": pred_time,
            "wall_clock_time": time.time() - self._start_time_flag,
            "metric_for_logging": metric_for_logging,
            "val_loss": val_loss,
            "trained_estimator": trained_estimator,
        }
        if sampled_weight is not None:
            self.fit_kwargs["sample_weight"] = weight
        return result

    def _train_with_config(
        self,
        estimator,
        config_w_resource,
        sample_size=None,
    ):
        if not sample_size:
            sample_size = config_w_resource.get(
                "FLAML_sample_size", len(self.y_train_all)
            )
        config = config_w_resource.get("ml", config_w_resource).copy()
        if "FLAML_sample_size" in config:
            del config["FLAML_sample_size"]
        if "learner" in config:
            del config["learner"]
        (
            sampled_X_train,
            sampled_y_train,
            sampled_weight,
            groups,
        ) = self._prepare_sample_train_data(sample_size)
        if sampled_weight is not None:
            weight = self.fit_kwargs["sample_weight"]
            self.fit_kwargs["sample_weight"] = sampled_weight
        else:
            weight = None
        if groups is not None:
            self.fit_kwargs["groups"] = groups
        budget = (
            None
            if self.time_budget is None
            else self.time_budget - self.time_from_start
        )
        if (
            hasattr(self, "resources_per_trial")
            and self.resources_per_trial.get("gpu", 0) > 0
        ):

            def _trainable_function_wrapper(config: dict):

                return_estimator, train_time = train_estimator(
                    X_train=sampled_X_train,
                    y_train=sampled_y_train,
                    config_dic=config,
                    task=self.task,
                    estimator_name=estimator,
                    n_jobs=self.n_jobs,
                    estimator_class=self.learner_classes.get(estimator),
                    budget=budget,
                    fit_kwargs=self.fit_kwargs,
                )
                return {"estimator": return_estimator, "train_time": train_time}

            if estimator not in self.learner_classes:
                self.learner_classes[estimator] = get_estimator_class(
                    self.task, estimator
                )

            analysis = tune.run(
                _trainable_function_wrapper,
                config=config_w_resource,
                metric="train_time",
                mode="min",
                resources_per_trial=self.resources_per_trial,
                num_samples=1,
                use_ray=True,
            )
            result = list(analysis.results.values())[0]
            estimator, train_time = result["estimator"], result["train_time"]
        else:
            if _is_nlp_task(self.task):
                use_ray = self.fit_kwargs.get("use_ray")
                self.fit_kwargs["use_ray"] = False
            estimator, train_time = train_estimator(
                X_train=sampled_X_train,
                y_train=sampled_y_train,
                config_dic=config,
                task=self.task,
                estimator_name=estimator,
                n_jobs=self.n_jobs,
                estimator_class=self.learner_classes.get(estimator),
                budget=budget,
                fit_kwargs=self.fit_kwargs,
            )
            if _is_nlp_task(self.task):
                if use_ray is None:
                    del self.fit_kwargs["use_ray"]
                else:
                    self.fit_kwargs["use_ray"] = use_ray
        if sampled_weight is not None:
            self.fit_kwargs["sample_weight"] = weight
        return estimator, train_time


def size(state: AutoMLState, config: dict) -> float:
    """Size function.

    Returns:
        The mem size in bytes for a config.
    """
    config = config.get("ml", config)
    estimator = config["learner"]
    learner_class = state.learner_classes.get(estimator)
    return learner_class.size(config)


class AutoML(BaseEstimator):
    """The AutoML class.
    Example:

    ```python
    automl = AutoML()
    automl_settings = {
        "time_budget": 60,
        "metric": 'accuracy',
        "task": 'classification',
        "log_file_name": 'mylog.log',
    }
    automl.fit(X_train = X_train, y_train = y_train, **automl_settings)
    ```

    """

    from .version import __version__

    def __init__(self, **settings):
        """Constructor.

        Many settings in fit() can be passed to the constructor too.
        If an argument in fit() is provided, it will override the setting passed to the constructor.
        If an argument in fit() is not provided but provided in the constructor, the value passed to the constructor will be used.

        Args:
            metric: A string of the metric name or a function,
                e.g., 'accuracy', 'roc_auc', 'roc_auc_ovr', 'roc_auc_ovo',
                'f1', 'micro_f1', 'macro_f1', 'log_loss', 'mae', 'mse', 'r2',
                'mape'. Default is 'auto'.
                If passing a customized metric function, the function needs to
                have the follwing signature:
        ```python
        def custom_metric(
            X_test, y_test, estimator, labels,
            X_train, y_train, weight_test=None, weight_train=None,
            config=None, groups_test=None, groups_train=None,
        ):
            return metric_to_minimize, metrics_to_log
        ```
                which returns a float number as the minimization objective,
                and a dictionary as the metrics to log. E.g.,
        ```python
        def custom_metric(
            X_val, y_val, estimator, labels,
            X_train, y_train, weight_val=None, weight_train=None,
            **args,
        ):
            from sklearn.metrics import log_loss
            import time

            start = time.time()
            y_pred = estimator.predict_proba(X_val)
            pred_time = (time.time() - start) / len(X_val)
            val_loss = log_loss(y_val, y_pred, labels=labels, sample_weight=weight_val)
            y_pred = estimator.predict_proba(X_train)
            train_loss = log_loss(y_train, y_pred, labels=labels, sample_weight=weight_train)
            alpha = 0.5
            return val_loss * (1 + alpha) - alpha * train_loss, {
                "val_loss": val_loss,
                "train_loss": train_loss,
                "pred_time": pred_time,
            }
        ```
            task: A string of the task type, e.g.,
                'classification', 'regression', 'ts_forecast', 'rank',
                'seq-classification', 'seq-regression', 'summarization'.
            n_jobs: An integer of the number of threads for training.
            log_file_name: A string of the log file name | default="". To disable logging,
                set it to be an empty string "".
            estimator_list: A list of strings for estimator names, or 'auto'
                e.g., ```['lgbm', 'xgboost', 'xgb_limitdepth', 'catboost', 'rf', 'extra_tree']```
            time_budget: A float number of the time budget in seconds.
                Use -1 if no time limit.
            max_iter: An integer of the maximal number of iterations.
            sample: A boolean of whether to sample the training data during
                search.
            ensemble: boolean or dict | default=False. Whether to perform
                ensemble after search. Can be a dict with keys 'passthrough'
                and 'final_estimator' to specify the passthrough and
                final_estimator in the stacker.
            eval_method: A string of resampling strategy, one of
                ['auto', 'cv', 'holdout'].
            split_ratio: A float of the valiation data percentage for holdout.
            n_splits: An integer of the number of folds for cross - validation.
            log_type: A string of the log type, one of
                ['better', 'all'].
                'better' only logs configs with better loss than previos iters
                'all' logs all the tried configs.
            model_history: A boolean of whether to keep the best
                model per estimator. Make sure memory is large enough if setting to True.
            log_training_metric: A boolean of whether to log the training
                metric for each model.
            mem_thres: A float of the memory size constraint in bytes.
            pred_time_limit: A float of the prediction latency constraint in seconds.
                It refers to the average prediction time per row in validation data.
            train_time_limit: A float of the training time constraint in seconds.
            verbose: int, default=3 | Controls the verbosity, higher means more
                messages.
            retrain_full: bool or str, default=True | whether to retrain the
                selected model on the full training data when using holdout.
                True - retrain only after search finishes; False - no retraining;
                'budget' - do best effort to retrain without violating the time
                budget.
            split_type: str or splitter object, default="auto" | the data split type.
                * A valid splitter object is an instance of a derived class of scikit-learn
                [KFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.KFold.html#sklearn.model_selection.KFold)
                and have ``split`` and ``get_n_splits`` methods with the same signatures.
                Set eval_method to "cv" to use the splitter object.
                * Valid str options depend on different tasks.
                For classification tasks, valid choices are
                    ["auto", 'stratified', 'uniform', 'time', 'group']. "auto" -> stratified.
                For regression tasks, valid choices are ["auto", 'uniform', 'time'].
                    "auto" -> uniform.
                For ts_forecast tasks, must be "auto" or 'time'.
                For ranking task, must be "auto" or 'group'.
            hpo_method: str, default="auto" | The hyperparameter
                optimization method. By default, CFO is used for sequential
                search and BlendSearch is used for parallel search.
                No need to set when using flaml's default search space or using
                a simple customized search space. When set to 'bs', BlendSearch
                is used. BlendSearch can be tried when the search space is
                complex, for example, containing multiple disjoint, discontinuous
                subspaces. When set to 'random', random search is used.
            starting_points: A dictionary to specify the starting hyperparameter
                config for the estimators.
                Keys are the name of the estimators, and values are the starting
                hyperparamter configurations for the corresponding estimators.
                The value can be a single hyperparamter configuration dict or a list
                of hyperparamter configuration dicts.
                In the following code example, we get starting_points from the
                `automl` object and use them in the `new_automl` object.
                e.g.,

        ```python
        from flaml import AutoML
        automl = AutoML()
        X_train, y_train = load_iris(return_X_y=True)
        automl.fit(X_train, y_train)
        starting_points = automl.best_config_per_estimator

        new_automl = AutoML()
        new_automl.fit(X_train, y_train, starting_points=starting_points)
        ```

            seed: int or None, default=None | The random seed for hpo.
            n_concurrent_trials: [Experimental] int, default=1 | The number of
                concurrent trials. For n_concurrent_trials > 1, installation of
                ray is required: `pip install flaml[ray]`.
            keep_search_state: boolean, default=False | Whether to keep data needed
                for model search after fit(). By default the state is deleted for
                space saving.
            early_stop: boolean, default=False | Whether to stop early if the
                search is considered to converge.
            append_log: boolean, default=False | Whetehr to directly append the log
                records to the input log file if it exists.
            auto_augment: boolean, default=True | Whether to automatically
                augment rare classes.
            min_sample_size: int, default=MIN_SAMPLE_TRAIN | the minimal sample
                size when sample=True.
            use_ray: boolean, default=False | Whether to use ray to run the training
                in separate processes. This can be used to prevent OOM for large
                datasets, but will incur more overhead in time. Only use it if
                you run into OOM failures.

        """
        self._track_iter = 0
        self._state = AutoMLState()
        self._state.learner_classes = {}
        self._settings = settings
        settings["time_budget"] = settings.get("time_budget", 60)
        settings["task"] = settings.get("task", "classification")
        settings["n_jobs"] = settings.get("n_jobs", -1)
        settings["eval_method"] = settings.get("eval_method", "auto")
        settings["split_ratio"] = settings.get("split_ratio", SPLIT_RATIO)
        settings["n_splits"] = settings.get("n_splits", N_SPLITS)
        settings["auto_augment"] = settings.get("auto_augment", True)
        settings["metric"] = settings.get("metric", "auto")
        settings["estimator_list"] = settings.get("estimator_list", "auto")
        settings["log_file_name"] = settings.get("log_file_name", "")
        settings["max_iter"] = settings.get("max_iter", 1000000)
        settings["sample"] = settings.get("sample", True)
        settings["ensemble"] = settings.get("ensemble", False)
        settings["log_type"] = settings.get("log_type", "better")
        settings["model_history"] = settings.get("model_history", False)
        settings["log_training_metric"] = settings.get("log_training_metric", False)
        settings["mem_thres"] = settings.get("mem_thres", MEM_THRES)
        settings["pred_time_limit"] = settings.get("pred_time_limit", np.inf)
        settings["train_time_limit"] = settings.get("train_time_limit", np.inf)
        settings["verbose"] = settings.get("verbose", 3)
        settings["retrain_full"] = settings.get("retrain_full", True)
        settings["split_type"] = settings.get("split_type", "auto")
        settings["hpo_method"] = settings.get("hpo_method", "auto")
        settings["learner_selector"] = settings.get("learner_selector", "sample")
        settings["starting_points"] = settings.get("starting_points", {})
        settings["n_concurrent_trials"] = settings.get("n_concurrent_trials", 1)
        settings["keep_search_state"] = settings.get("keep_search_state", False)
        settings["early_stop"] = settings.get("early_stop", False)
        settings["append_log"] = settings.get("append_log", False)
        settings["min_sample_size"] = settings.get("min_sample_size", MIN_SAMPLE_TRAIN)
        settings["use_ray"] = settings.get("use_ray", False)
        self._estimator_type = (
            "classifier" if settings["task"] in CLASSIFICATION else "regressor"
        )

    def get_params(self, deep=False):
        return self._settings.copy()

    @property
    def config_history(self):
        """A dictionary of iter->(estimator, config, time),
        storing the best estimator, config, and the time when the best
        model is updated each time.
        """
        return self._config_history

    @property
    def model(self):
        """An object with `predict()` and `predict_proba()` method (for
        classification), storing the best trained model.
        """
        return self.__dict__.get("_trained_estimator")

    def best_model_for_estimator(self, estimator_name):
        """Return the best model found for a particular estimator.

        Args:
            estimator_name: a str of the estimator's name.

        Returns:
            An object storing the best model for estimator_name.
            If `model_history` was set to False during fit(), then the returned model
            is untrained unless estimator_name is the best estimator.
            If `model_history` was set to True, then the returned model is trained.
        """
        state = self._search_states.get(estimator_name)
        return state and getattr(state, "trained_estimator", None)

    @property
    def best_estimator(self):
        """A string indicating the best estimator found."""
        return self._best_estimator

    @property
    def best_iteration(self):
        """An integer of the iteration number where the best
        config is found."""
        return self._best_iteration

    @property
    def best_config(self):
        """A dictionary of the best configuration."""
        state = self._search_states.get(self._best_estimator)
        return state and getattr(state, "best_config", None)

    @property
    def best_config_per_estimator(self):
        """A dictionary of all estimators' best configuration."""
        return {
            e: e_search_state.best_config
            for e, e_search_state in self._search_states.items()
        }

    @property
    def best_loss_per_estimator(self):
        """A dictionary of all estimators' best loss."""
        return {
            e: e_search_state.best_loss
            for e, e_search_state in self._search_states.items()
        }

    @property
    def best_loss(self):
        """A float of the best loss found."""
        return self._state.best_loss

    @property
    def best_config_train_time(self):
        """A float of the seconds taken by training the best config."""
        return getattr(
            self._search_states[self._best_estimator], "best_config_train_time", None
        )

    def save_best_config(self, filename):
        best = {
            "class": self.best_estimator,
            "hyperparameters": self.best_config,
        }
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump(best, f)

    @property
    def classes_(self):
        """A list of n_classes elements for class labels."""
        attr = getattr(self, "_label_transformer", None)
        if attr:
            return attr.classes_.tolist()
        attr = getattr(self, "_trained_estimator", None)
        if attr:
            return attr.classes_.tolist()
        return None

    @property
    def n_features_in_(self):
        return self._trained_estimator.n_features_in_

    @property
    def time_to_find_best_model(self) -> float:
        """Time taken to find best model in seconds."""
        return self.__dict__.get("_time_taken_best_iter")

    def predict(self, X: Union[np.array, pd.DataFrame, List[str], List[List[str]]]):
        """Predict label from features.

        Args:
            X: A numpy array of featurized instances, shape n * m,
                or for 'ts_forecast' task:
                    a pandas dataframe with the first column containing
                    timestamp values (datetime type) or an integer n for
                    the predict steps (only valid when the estimator is
                    arima or sarimax). Other columns in the dataframe
                    are assumed to be exogenous variables (categorical
                    or numeric).

        ```python
        multivariate_X_test = pd.DataFrame({
            'timeStamp': pd.date_range(start='1/1/2022', end='1/07/2022'),
            'categorical_col': ['yes', 'yes', 'no', 'no', 'yes', 'no', 'yes'],
            'continuous_col': [105, 107, 120, 118, 110, 112, 115]
        })
        model.predict(multivariate_X_test)
        ```

        Returns:
            A array-like of shape n * 1: each element is a predicted
            label for an instance.
        """
        estimator = getattr(self, "_trained_estimator", None)
        if estimator is None:
            logger.warning(
                "No estimator is trained. Please run fit with enough budget."
            )
            return None
        X = self._preprocess(X)
        y_pred = estimator.predict(X)
        if (
            isinstance(y_pred, np.ndarray)
            and y_pred.ndim > 1
            and isinstance(y_pred, np.ndarray)
        ):
            y_pred = y_pred.flatten()
        if self._label_transformer:
            return self._label_transformer.inverse_transform(
                pd.Series(y_pred.astype(int))
            )
        else:
            return y_pred

    def predict_proba(self, X):
        """Predict the probability of each class from features, only works for
        classification problems.

        Args:
            X: A numpy array of featurized instances, shape n * m.

        Returns:
            A numpy array of shape n * c. c is the  # classes. Each element at
            (i, j) is the probability for instance i to be in class j.
        """
        estimator = getattr(self, "_trained_estimator", None)
        if estimator is None:
            logger.warning(
                "No estimator is trained. Please run fit with enough budget."
            )
            return None
        X = self._preprocess(X)
        proba = self._trained_estimator.predict_proba(X)
        return proba

    def _preprocess(self, X):
        if isinstance(X, List):
            try:
                if isinstance(X[0], List):
                    X = [x for x in zip(*X)]
                X = pd.DataFrame(
                    dict(
                        [
                            (self._transformer._str_columns[idx], X[idx])
                            if isinstance(X[0], List)
                            else (self._transformer._str_columns[idx], [X[idx]])
                            for idx in range(len(X))
                        ]
                    )
                )
            except IndexError:
                raise IndexError(
                    "Test data contains more columns than training data, exiting"
                )
        elif isinstance(X, int):
            return X
        elif issparse(X):
            X = X.tocsr()
        if self._state.task == TS_FORECAST:
            X = pd.DataFrame(X)
        if self._transformer:
            X = self._transformer.transform(X)
        return X

    def _validate_ts_data(
        self,
        dataframe,
        y_train_all=None,
    ):
        assert (
            dataframe[dataframe.columns[0]].dtype.name == "datetime64[ns]"
        ), f"For '{TS_FORECAST}' task, the first column must contain timestamp values."
        if y_train_all is not None:
            y_df = (
                pd.DataFrame(y_train_all)
                if isinstance(y_train_all, pd.Series)
                else pd.DataFrame(y_train_all, columns=["labels"])
            )
            dataframe = dataframe.join(y_df)
        duplicates = dataframe.duplicated()
        if any(duplicates):
            logger.warning(
                "Duplicate timestamp values found in timestamp column. "
                f"\n{dataframe.loc[duplicates, dataframe][dataframe.columns[0]]}"
            )
            dataframe = dataframe.drop_duplicates()
            logger.warning("Removed duplicate rows based on all columns")
            assert (
                dataframe[[dataframe.columns[0]]].duplicated() is None
            ), "Duplicate timestamp values with different values for other columns."
        ts_series = pd.to_datetime(dataframe[dataframe.columns[0]])
        inferred_freq = pd.infer_freq(ts_series)
        if inferred_freq is None:
            logger.warning(
                "Missing timestamps detected. To avoid error with estimators, set estimator list to ['prophet']. "
            )
        if y_train_all is not None:
            return dataframe.iloc[:, :-1], dataframe.iloc[:, -1]
        return dataframe

    def _validate_data(
        self,
        X_train_all,
        y_train_all,
        dataframe,
        label,
        X_val=None,
        y_val=None,
        groups_val=None,
        groups=None,
    ):

        if X_train_all is not None and y_train_all is not None:
            assert (
                isinstance(X_train_all, np.ndarray)
                or issparse(X_train_all)
                or isinstance(X_train_all, pd.DataFrame)
            ), (
                "X_train_all must be a numpy array, a pandas dataframe, "
                "or Scipy sparse matrix."
            )
            assert isinstance(y_train_all, np.ndarray) or isinstance(
                y_train_all, pd.Series
            ), "y_train_all must be a numpy array or a pandas series."
            assert (
                X_train_all.size != 0 and y_train_all.size != 0
            ), "Input data must not be empty."
            if isinstance(X_train_all, np.ndarray) and len(X_train_all.shape) == 1:
                X_train_all = np.reshape(X_train_all, (X_train_all.size, 1))
            if isinstance(y_train_all, np.ndarray):
                y_train_all = y_train_all.flatten()
            assert (
                X_train_all.shape[0] == y_train_all.shape[0]
            ), "# rows in X_train must match length of y_train."
            self._df = isinstance(X_train_all, pd.DataFrame)
            self._nrow, self._ndim = X_train_all.shape
            if self._state.task == TS_FORECAST:
                X_train_all = pd.DataFrame(X_train_all)
                X_train_all, y_train_all = self._validate_ts_data(
                    X_train_all, y_train_all
                )
            X, y = X_train_all, y_train_all
        elif dataframe is not None and label is not None:
            assert isinstance(
                dataframe, pd.DataFrame
            ), "dataframe must be a pandas DataFrame"
            assert label in dataframe.columns, "label must a column name in dataframe"
            self._df = True
            if self._state.task == TS_FORECAST:
                dataframe = self._validate_ts_data(dataframe)
            X = dataframe.drop(columns=label)
            self._nrow, self._ndim = X.shape
            y = dataframe[label]
        else:
            raise ValueError("either X_train+y_train or dataframe+label are required")

        # check the validity of input dimensions under the nlp mode
        if _is_nlp_task(self._state.task):
            from .nlp.utils import is_a_list_of_str

            is_all_str = True
            is_all_list = True
            for column in X.columns:
                assert X[column].dtype.name in (
                    "object",
                    "string",
                ), "If the task is an NLP task, X can only contain text columns"
                for each_cell in X[column]:
                    if each_cell is not None:
                        is_str = isinstance(each_cell, str)
                        is_list_of_int = isinstance(each_cell, list) and all(
                            isinstance(x, int) for x in each_cell
                        )
                        is_list_of_str = is_a_list_of_str(each_cell)
                        if self._state.task == TOKENCLASSIFICATION:
                            assert is_list_of_str, (
                                "For the token-classification task, the input column needs to be a list of string,"
                                "instead of string, e.g., ['EU', 'rejects','German', 'call','to','boycott','British','lamb','.',].",
                                "For more examples, please refer to test/nlp/test_autohf_tokenclassification.py",
                            )
                        else:
                            assert is_str or is_list_of_int, (
                                "Each column of the input must either be str (untokenized) "
                                "or a list of integers (tokenized)"
                            )
                        is_all_str &= is_str
                        is_all_list &= is_list_of_int or is_list_of_str
            assert is_all_str or is_all_list, (
                "Currently FLAML only supports two modes for NLP: either all columns of X are string (non-tokenized), "
                "or all columns of X are integer ids (tokenized)"
            )

        if issparse(X_train_all):
            self._transformer = self._label_transformer = False
            self._X_train_all, self._y_train_all = X, y
        else:
            from .data import DataTransformer

            self._transformer = DataTransformer()
            self._X_train_all, self._y_train_all = self._transformer.fit_transform(
                X, y, self._state.task
            )
            self._label_transformer = self._transformer.label_transformer
        self._sample_weight_full = self._state.fit_kwargs.get("sample_weight")
        if X_val is not None and y_val is not None:
            assert (
                isinstance(X_val, np.ndarray)
                or issparse(X_val)
                or isinstance(X_val, pd.DataFrame)
            ), (
                "X_val must be None, a numpy array, a pandas dataframe, "
                "or Scipy sparse matrix."
            )
            assert isinstance(y_val, np.ndarray) or isinstance(
                y_val, pd.Series
            ), "y_val must be None, a numpy array or a pandas series."
            assert X_val.size != 0 and y_val.size != 0, (
                "Validation data are expected to be nonempty. "
                "Use None for X_val and y_val if no validation data."
            )
            if isinstance(y_val, np.ndarray):
                y_val = y_val.flatten()
            assert (
                X_val.shape[0] == y_val.shape[0]
            ), "# rows in X_val must match length of y_val."
            if self._transformer:
                self._state.X_val = self._transformer.transform(X_val)
            else:
                self._state.X_val = X_val
            # If it's NLG_TASKS, y_val is a pandas series containing the output sequence tokens,
            # so we cannot use label_transformer.transform to process it
            if self._label_transformer:
                self._state.y_val = self._label_transformer.transform(y_val)
            else:
                self._state.y_val = y_val
        else:
            self._state.X_val = self._state.y_val = None
        if groups is not None and len(groups) != self._nrow:
            # groups is given as group counts
            self._state.groups = np.concatenate([[i] * c for i, c in enumerate(groups)])
            assert (
                len(self._state.groups) == self._nrow
            ), "the sum of group counts must match the number of examples"
            self._state.groups_val = (
                np.concatenate([[i] * c for i, c in enumerate(groups_val)])
                if groups_val is not None
                else None
            )
        else:
            self._state.groups_val = groups_val
            self._state.groups = groups

    def _prepare_data(self, eval_method, split_ratio, n_splits):

        X_val, y_val = self._state.X_val, self._state.y_val
        if issparse(X_val):
            X_val = X_val.tocsr()
        X_train_all, y_train_all = self._X_train_all, self._y_train_all
        if issparse(X_train_all):
            X_train_all = X_train_all.tocsr()
        if (
            self._state.task in CLASSIFICATION
            and self._auto_augment
            and self._state.fit_kwargs.get("sample_weight") is None
            and self._split_type in ["stratified", "uniform"]
            and self._state.task != TOKENCLASSIFICATION
        ):
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
                        X_train_all = concat(
                            X_train_all, X_train_all.iloc[:n].loc[rare_index]
                        )
                    else:
                        X_train_all = concat(
                            X_train_all, X_train_all[:n][rare_index, :]
                        )
                    if isinstance(y_train_all, pd.Series):
                        y_train_all = concat(
                            y_train_all, y_train_all.iloc[:n].loc[rare_index]
                        )
                    else:
                        y_train_all = np.concatenate(
                            [y_train_all, y_train_all[:n][rare_index]]
                        )
                    count += rare_count
                logger.info(f"class {label} augmented from {rare_count} to {count}")
        SHUFFLE_SPLIT_TYPES = ["uniform", "stratified"]
        if self._split_type in SHUFFLE_SPLIT_TYPES:
            if self._sample_weight_full is not None:
                X_train_all, y_train_all, self._state.sample_weight_all = shuffle(
                    X_train_all,
                    y_train_all,
                    self._sample_weight_full,
                    random_state=RANDOM_SEED,
                )
                self._state.fit_kwargs["sample_weight"] = self._state.sample_weight_all
            else:
                X_train_all, y_train_all = shuffle(
                    X_train_all, y_train_all, random_state=RANDOM_SEED
                )
            if self._df:
                X_train_all.reset_index(drop=True, inplace=True)
                if isinstance(y_train_all, pd.Series):
                    y_train_all.reset_index(drop=True, inplace=True)

        X_train, y_train = X_train_all, y_train_all
        self._state.groups_all = self._state.groups
        if X_val is None and eval_method == "holdout":
            # if eval_method = holdout, make holdout data
            if self._split_type == "time":
                if self._state.task == TS_FORECAST:
                    num_samples = X_train_all.shape[0]
                    period = self._state.fit_kwargs["period"]
                    assert (
                        period < num_samples
                    ), f"period={period}>#examples={num_samples}"
                    split_idx = num_samples - period
                    X_train = X_train_all[:split_idx]
                    y_train = y_train_all[:split_idx]
                    X_val = X_train_all[split_idx:]
                    y_val = y_train_all[split_idx:]
                else:
                    if "sample_weight" in self._state.fit_kwargs:
                        (
                            X_train,
                            X_val,
                            y_train,
                            y_val,
                            self._state.fit_kwargs["sample_weight"],
                            self._state.weight_val,
                        ) = train_test_split(
                            X_train_all,
                            y_train_all,
                            self._state.fit_kwargs["sample_weight"],
                            test_size=split_ratio,
                            shuffle=False,
                        )
                    else:
                        X_train, X_val, y_train, y_val = train_test_split(
                            X_train_all,
                            y_train_all,
                            test_size=split_ratio,
                            shuffle=False,
                        )
            elif self._split_type == "group":
                gss = GroupShuffleSplit(
                    n_splits=1, test_size=split_ratio, random_state=RANDOM_SEED
                )
                for train_idx, val_idx in gss.split(
                    X_train_all, y_train_all, self._state.groups_all
                ):
                    if self._df:
                        X_train = X_train_all.iloc[train_idx]
                        X_val = X_train_all.iloc[val_idx]
                    else:
                        X_train, X_val = X_train_all[train_idx], X_train_all[val_idx]
                    y_train, y_val = y_train_all[train_idx], y_train_all[val_idx]
                    self._state.groups = self._state.groups_all[train_idx]
                    self._state.groups_val = self._state.groups_all[val_idx]
            elif self._state.task in CLASSIFICATION:
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
                X_first = X_train_all.iloc[first] if self._df else X_train_all[first]
                X_rest = X_train_all.iloc[rest] if self._df else X_train_all[rest]
                y_rest = y_train_all[rest]
                stratify = y_rest if self._split_type == "stratified" else None
                if "sample_weight" in self._state.fit_kwargs:
                    (
                        X_train,
                        X_val,
                        y_train,
                        y_val,
                        weight_train,
                        weight_val,
                    ) = train_test_split(
                        X_rest,
                        y_rest,
                        self._state.fit_kwargs["sample_weight"][rest],
                        test_size=split_ratio,
                        random_state=RANDOM_SEED,
                    )
                    weight1 = self._state.fit_kwargs["sample_weight"][first]
                    self._state.weight_val = concat(weight1, weight_val)
                    self._state.fit_kwargs["sample_weight"] = concat(
                        weight1, weight_train
                    )
                else:
                    X_train, X_val, y_train, y_val = train_test_split(
                        X_rest,
                        y_rest,
                        test_size=split_ratio,
                        stratify=stratify,
                        random_state=RANDOM_SEED,
                    )
                X_train = concat(X_first, X_train)
                y_train = (
                    concat(label_set, y_train)
                    if self._df
                    else np.concatenate([label_set, y_train])
                )
                X_val = concat(X_first, X_val)
                y_val = (
                    concat(label_set, y_val)
                    if self._df
                    else np.concatenate([label_set, y_val])
                )
            elif self._state.task in REGRESSION:
                if "sample_weight" in self._state.fit_kwargs:
                    (
                        X_train,
                        X_val,
                        y_train,
                        y_val,
                        self._state.fit_kwargs["sample_weight"],
                        self._state.weight_val,
                    ) = train_test_split(
                        X_train_all,
                        y_train_all,
                        self._state.fit_kwargs["sample_weight"],
                        test_size=split_ratio,
                        random_state=RANDOM_SEED,
                    )
                else:
                    X_train, X_val, y_train, y_val = train_test_split(
                        X_train_all,
                        y_train_all,
                        test_size=split_ratio,
                        random_state=RANDOM_SEED,
                    )
        self._state.data_size = X_train.shape
        self.data_size_full = len(y_train_all)
        self._state.X_train, self._state.y_train = X_train, y_train
        self._state.X_val, self._state.y_val = X_val, y_val
        self._state.X_train_all = X_train_all
        self._state.y_train_all = y_train_all
        if eval_method == "holdout":
            self._state.kf = None
            return
        if self._split_type == "group":
            # logger.info("Using GroupKFold")
            assert (
                len(self._state.groups_all) == y_train_all.size
            ), "the length of groups must match the number of examples"
            assert (
                len(np.unique(self._state.groups_all)) >= n_splits
            ), "the number of groups must be equal or larger than n_splits"
            self._state.kf = GroupKFold(n_splits)
            self._state.kf.groups = self._state.groups_all
        elif self._split_type == "stratified":
            # logger.info("Using StratifiedKFold")
            assert y_train_all.size >= n_splits, (
                f"{n_splits}-fold cross validation"
                f" requires input data with at least {n_splits} examples."
            )
            assert y_train_all.size >= 2 * n_splits, (
                f"{n_splits}-fold cross validation with metric=r2 "
                f"requires input data with at least {n_splits*2} examples."
            )
            self._state.kf = RepeatedStratifiedKFold(
                n_splits=n_splits, n_repeats=1, random_state=RANDOM_SEED
            )
        elif self._split_type == "time":
            # logger.info("Using TimeSeriesSplit")
            if self._state.task == TS_FORECAST:
                period = self._state.fit_kwargs["period"]
                if period * (n_splits + 1) > y_train_all.size:
                    n_splits = int(y_train_all.size / period - 1)
                    assert n_splits >= 2, (
                        f"cross validation for forecasting period={period}"
                        f" requires input data with at least {3 * period} examples."
                    )
                    logger.info(f"Using nsplits={n_splits} due to data size limit.")
                self._state.kf = TimeSeriesSplit(n_splits=n_splits, test_size=period)
            else:
                self._state.kf = TimeSeriesSplit(n_splits=n_splits)
        elif isinstance(self._split_type, str):
            # logger.info("Using RepeatedKFold")
            self._state.kf = RepeatedKFold(
                n_splits=n_splits, n_repeats=1, random_state=RANDOM_SEED
            )
        else:
            # logger.info("Using splitter object")
            self._state.kf = self._split_type

    def add_learner(self, learner_name, learner_class):
        """Add a customized learner.

        Args:
            learner_name: A string of the learner's name.
            learner_class: A subclass of flaml.model.BaseEstimator.
        """
        self._state.learner_classes[learner_name] = learner_class

    def get_estimator_from_log(self, log_file_name, record_id, task):
        """Get the estimator from log file.

        Args:
            log_file_name: A string of the log file name.
            record_id: An integer of the record ID in the file,
                0 corresponds to the first trial.
            task: A string of the task type,
                'binary', 'multi', 'regression', 'ts_forecast', 'rank'.

        Returns:
            An estimator object for the given configuration.
        """

        with training_log_reader(log_file_name) as reader:
            record = reader.get_record(record_id)
            estimator = record.learner
            config = record.config

        estimator, _ = train_estimator(
            X_train=None,
            y_train=None,
            config_dic=config,
            task=task,
            estimator_name=estimator,
            estimator_class=self._state.learner_classes.get(estimator),
        )
        return estimator

    def retrain_from_log(
        self,
        log_file_name,
        X_train=None,
        y_train=None,
        dataframe=None,
        label=None,
        time_budget=np.inf,
        task=None,
        eval_method=None,
        split_ratio=None,
        n_splits=None,
        split_type=None,
        groups=None,
        n_jobs=-1,
        # gpu_per_trial=0,
        train_best=True,
        train_full=False,
        record_id=-1,
        auto_augment=None,
        **fit_kwargs,
    ):
        """Retrain from log file.

        Args:
            log_file_name: A string of the log file name.
            X_train: A numpy array or dataframe of training data in shape n*m.
                For 'ts_forecast' task, the first column of X_train
                must be the timestamp column (datetime type). Other
                columns in the dataframe are assumed to be exogenous
                variables (categorical or numeric).
            y_train: A numpy array or series of labels in shape n*1.
            dataframe: A dataframe of training data including label column.
                For 'ts_forecast' task, dataframe must be specified and should
                have at least two columns: timestamp and label, where the first
                column is the timestamp column (datetime type). Other columns
                in the dataframe are assumed to be exogenous variables
                (categorical or numeric).
            label: A str of the label column name, e.g., 'label';
                Note: If X_train and y_train are provided,
                dataframe and label are ignored;
                If not, dataframe and label must be provided.
            time_budget: A float number of the time budget in seconds.
            task: A string of the task type, e.g.,
                'classification', 'regression', 'ts_forecast', 'rank',
                'seq-classification', 'seq-regression', 'summarization'.
            eval_method: A string of resampling strategy, one of
                ['auto', 'cv', 'holdout'].
            split_ratio: A float of the validation data percentage for holdout.
            n_splits: An integer of the number of folds for cross-validation.
            split_type: str or splitter object, default="auto" | the data split type.
                * A valid splitter object is an instance of a derived class of scikit-learn
                [KFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.KFold.html#sklearn.model_selection.KFold)
                and have ``split`` and ``get_n_splits`` methods with the same signatures.
                Set eval_method to "cv" to use the splitter object.
                * Valid str options depend on different tasks.
                For classification tasks, valid choices are
                    ["auto", 'stratified', 'uniform', 'time', 'group']. "auto" -> stratified.
                For regression tasks, valid choices are ["auto", 'uniform', 'time'].
                    "auto" -> uniform.
                For ts_forecast tasks, must be "auto" or 'time'.
                For ranking task, must be "auto" or 'group'.
            groups: None or array-like | Group labels (with matching length to
                y_train) or groups counts (with sum equal to length of y_train)
                for training data.
            n_jobs: An integer of the number of threads for training. Use all
                available resources when n_jobs == -1.
            train_best: A boolean of whether to train the best config in the
                time budget; if false, train the last config in the budget.
            train_full: A boolean of whether to train on the full data. If true,
                eval_method and sample_size in the log file will be ignored.
            record_id: the ID of the training log record from which the model will
                be retrained. By default `record_id = -1` which means this will be
                ignored. `record_id = 0` corresponds to the first trial, and
                when `record_id >= 0`, `time_budget` will be ignored.
            auto_augment: boolean, default=True | Whether to automatically
                augment rare classes.
            **fit_kwargs: Other key word arguments to pass to fit() function of
                the searched learners, such as sample_weight.
        """
        task = task or self._settings.get("task")
        eval_method = eval_method or self._settings.get("eval_method")
        split_ratio = split_ratio or self._settings.get("split_ratio")
        n_splits = n_splits or self._settings.get("n_splits")
        split_type = split_type or self._settings.get("split_type")
        auto_augment = (
            self._settings.get("auto_augment") if auto_augment is None else auto_augment
        )
        self._state.task = TS_FORECAST if task == FORECAST else task
        self._estimator_type = "classifier" if task in CLASSIFICATION else "regressor"

        self._state.fit_kwargs = fit_kwargs
        self._validate_data(X_train, y_train, dataframe, label, groups=groups)

        logger.info("log file name {}".format(log_file_name))

        best_config = None
        best_val_loss = float("+inf")
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
                    logger.warning(
                        f"No estimator found within time_budget={time_budget}"
                    )
                    from .model import BaseEstimator as Estimator

                    self._trained_estimator = Estimator()
                    return training_duration
        if not best:
            return
        best_estimator = best.learner
        best_config = best.config
        sample_size = len(self._y_train_all) if train_full else best.sample_size

        logger.info(
            "estimator = {}, config = {}, #training instances = {}".format(
                best_estimator, best_config, sample_size
            )
        )
        # Partially copied from fit() function
        # Initilize some attributes required for retrain_from_log
        self._decide_split_type(split_type)
        if record_id >= 0:
            eval_method = "cv"
        elif eval_method == "auto":
            eval_method = self._decide_eval_method(time_budget)
        self.modelcount = 0
        self._auto_augment = auto_augment
        self._prepare_data(eval_method, split_ratio, n_splits)
        self._state.time_budget = None
        self._state.n_jobs = n_jobs
        import os

        self._state.resources_per_trial = (
            {"cpu": os.cpu_count(), "gpu": fit_kwargs.get("gpu_per_trial", 0)}
            if self._state.n_jobs < 0
            else {"cpu": self._state.n_jobs, "gpu": fit_kwargs.get("gpu_per_trial", 0)}
        )
        self._trained_estimator = self._state._train_with_config(
            best_estimator,
            best_config,
            sample_size=sample_size,
        )[0]
        logger.info("retrain from log succeeded")
        return training_duration

    def _decide_split_type(self, split_type):
        if self._state.task == "classification":
            self._state.task = get_classification_objective(
                len(np.unique(self._y_train_all))
            )
        if not isinstance(split_type, str):
            assert hasattr(split_type, "split") and hasattr(
                split_type, "get_n_splits"
            ), "split_type must be a string or a splitter object with split and get_n_splits methods."
            self._split_type = split_type
        elif self._state.task in CLASSIFICATION:
            assert split_type in ["auto", "stratified", "uniform", "time", "group"]
            self._split_type = (
                split_type
                if split_type != "auto"
                else self._state.groups is None and "stratified" or "group"
            )
        elif self._state.task in REGRESSION:
            assert split_type in ["auto", "uniform", "time", "group"]
            self._split_type = split_type if split_type != "auto" else "uniform"
        elif self._state.task == TS_FORECAST:
            assert split_type in ["auto", "time"]
            self._split_type = "time"
            assert isinstance(
                self._state.fit_kwargs.get("period"), int
            ), f"missing a required integer 'period' for '{TS_FORECAST}' task."
        elif self._state.task == "rank":
            assert (
                self._state.groups is not None
            ), "groups must be specified for ranking task."
            assert split_type in ["auto", "group"]
            self._split_type = "group"
        elif self._state.task in NLG_TASKS:
            assert split_type in ["auto", "uniform", "time", "group"]
            self._split_type = split_type if split_type != "auto" else "uniform"

    def _decide_eval_method(self, time_budget):
        if self._state.X_val is not None:
            return "holdout"
        nrow, dim = self._nrow, self._ndim
        if (
            time_budget is None
            or nrow * dim / 0.9 < SMALL_LARGE_THRES * (time_budget / 3600)
            and nrow < CV_HOLDOUT_THRESHOLD
        ):
            # time allows or sampling can be used and cv is necessary
            return "cv"
        else:
            return "holdout"

    @property
    def search_space(self) -> dict:
        """Search space.

        Must be called after fit(...)
        (use max_iter=0 and retrain_final=False to prevent actual fitting).

        Returns:
            A dict of the search space.
        """
        estimator_list = self.estimator_list
        if len(estimator_list) == 1:
            estimator = estimator_list[0]
            space = self._search_states[estimator].search_space.copy()
            space["learner"] = estimator
            return space
        choices = []
        for estimator in estimator_list:
            space = self._search_states[estimator].search_space.copy()
            space["learner"] = estimator
            choices.append(space)
        return {"ml": tune.choice(choices)}

    @property
    def low_cost_partial_config(self) -> dict:
        """Low cost partial config.

        Returns:
            A dict.
            (a) if there is only one estimator in estimator_list, each key is a
            hyperparameter name.
            (b) otherwise, it is a nested dict with 'ml' as the key, and
            a list of the low_cost_partial_configs as the value, corresponding
            to each learner's low_cost_partial_config; the estimator index as
            an integer corresponding to the cheapest learner is appended to the
            list at the end.
        """
        if len(self.estimator_list) == 1:
            estimator = self.estimator_list[0]
            c = self._search_states[estimator].low_cost_partial_config
            return c
        else:
            configs = []
            for estimator in self.estimator_list:
                c = self._search_states[estimator].low_cost_partial_config
                configs.append(c)
            configs.append(
                np.argmin(
                    [
                        self._state.learner_classes.get(estimator).cost_relative2lgbm()
                        for estimator in self.estimator_list
                    ]
                )
            )
            config = {"ml": configs}
        return config

    @property
    def cat_hp_cost(self) -> dict:
        """Categorical hyperparameter cost

        Returns:
            A dict.
            (a) if there is only one estimator in estimator_list, each key is a
            hyperparameter name.
            (b) otherwise, it is a nested dict with 'ml' as the key, and
            a list of the cat_hp_cost's as the value, corresponding
            to each learner's cat_hp_cost; the cost relative to lgbm for each
            learner (as a list itself) is appended to the list at the end.
        """
        if len(self.estimator_list) == 1:
            estimator = self.estimator_list[0]
            c = self._search_states[estimator].cat_hp_cost
            return c
        else:
            configs = []
            for estimator in self.estimator_list:
                c = self._search_states[estimator].cat_hp_cost
                configs.append(c)
            configs.append(
                [
                    self._state.learner_classes.get(estimator).cost_relative2lgbm()
                    for estimator in self.estimator_list
                ]
            )
            config = {"ml": configs}
        return config

    @property
    def points_to_evaluate(self) -> dict:
        """Initial points to evaluate.

        Returns:
            A list of dicts. Each dict is the initial point for each learner.
        """
        points = []
        for estimator in self.estimator_list:
            if isinstance(self._search_states[estimator].init_config, list):
                configs = self._search_states[estimator].init_config
            else:
                configs = [self._search_states[estimator].init_config]
            for config in configs:
                config["learner"] = estimator
                if len(self.estimator_list) > 1:
                    points.append({"ml": config})
                else:
                    points.append(config)
        return points

    @property
    def resource_attr(self) -> Optional[str]:
        """Attribute of the resource dimension.

        Returns:
            A string for the sample size attribute
            (the resource attribute in AutoML) or None.
        """
        return "FLAML_sample_size" if self._sample else None

    @property
    def min_resource(self) -> Optional[float]:
        """Attribute for pruning.

        Returns:
            A float for the minimal sample size or None.
        """
        return self._min_sample_size if self._sample else None

    @property
    def max_resource(self) -> Optional[float]:
        """Attribute for pruning.

        Returns:
            A float for the maximal sample size or None.
        """
        return self._state.data_size[0] if self._sample else None

    @property
    def trainable(self) -> Callable[[dict], Optional[float]]:
        """Training function.

        Returns:
            A function that evaluates each config and returns the loss.
        """
        self._state.time_from_start = 0
        for estimator in self.estimator_list:
            search_state = self._search_states[estimator]
            if not hasattr(search_state, "training_function"):
                search_state.training_function = partial(
                    AutoMLState._compute_with_config_base, self._state, estimator
                )
        states = self._search_states
        mem_res = self._mem_thres

        def train(config: dict):

            sample_size = config.get("FLAML_sample_size")
            config = config.get("ml", config).copy()
            if sample_size:
                config["FLAML_sample_size"] = sample_size
            estimator = config["learner"]
            # check memory constraints before training
            if states[estimator].learner_class.size(config) <= mem_res:
                del config["learner"]
                result = states[estimator].training_function(config)
                return result
            else:
                return {
                    "pred_time": 0,
                    "wall_clock_time": None,
                    "metric_for_logging": np.inf,
                    "val_loss": np.inf,
                    "trained_estimator": None,
                }

        return train

    @property
    def metric_constraints(self) -> list:
        """Metric constraints.

        Returns:
            A list of the metric constraints.
        """
        constraints = []
        if np.isfinite(self._pred_time_limit):
            constraints.append(("pred_time", "<=", self._pred_time_limit))
        return constraints

    def fit(
        self,
        X_train=None,
        y_train=None,
        dataframe=None,
        label=None,
        metric=None,
        task=None,
        n_jobs=None,
        # gpu_per_trial=0,
        log_file_name=None,
        estimator_list=None,
        time_budget=None,
        max_iter=None,
        sample=None,
        ensemble=None,
        eval_method=None,
        log_type=None,
        model_history=None,
        split_ratio=None,
        n_splits=None,
        log_training_metric=None,
        mem_thres=None,
        pred_time_limit=None,
        train_time_limit=None,
        X_val=None,
        y_val=None,
        sample_weight_val=None,
        groups_val=None,
        groups=None,
        verbose=None,
        retrain_full=None,
        split_type=None,
        learner_selector=None,
        hpo_method=None,
        starting_points=None,
        seed=None,
        n_concurrent_trials=None,
        keep_search_state=None,
        early_stop=None,
        append_log=None,
        auto_augment=None,
        min_sample_size=None,
        use_ray=None,
        **fit_kwargs,
    ):
        """Find a model for a given task.

        Args:
            X_train: A numpy array or a pandas dataframe of training data in
                shape (n, m). For 'ts_forecast' task, the first column of X_train
                must be the timestamp column (datetime type). Other columns in
                the dataframe are assumed to be exogenous variables (categorical or numeric).
            y_train: A numpy array or a pandas series of labels in shape (n, ).
            dataframe: A dataframe of training data including label column.
                For 'ts_forecast' task, dataframe must be specified and must have
                at least two columns, timestamp and label, where the first
                column is the timestamp column (datetime type). Other columns in
                the dataframe are assumed to be exogenous variables (categorical or numeric).
            label: A str of the label column name for, e.g., 'label';
                Note: If X_train and y_train are provided,
                dataframe and label are ignored;
                If not, dataframe and label must be provided.
            metric: A string of the metric name or a function,
                e.g., 'accuracy', 'roc_auc', 'roc_auc_ovr', 'roc_auc_ovo',
                'f1', 'micro_f1', 'macro_f1', 'log_loss', 'mae', 'mse', 'r2',
                'mape'. Default is 'auto'.
                If passing a customized metric function, the function needs to
                have the follwing signature:
        ```python
        def custom_metric(
            X_test, y_test, estimator, labels,
            X_train, y_train, weight_test=None, weight_train=None,
            config=None, groups_test=None, groups_train=None,
        ):
            return metric_to_minimize, metrics_to_log
        ```
                which returns a float number as the minimization objective,
                and a dictionary as the metrics to log. E.g.,
        ```python
        def custom_metric(
            X_val, y_val, estimator, labels,
            X_train, y_train, weight_val=None, weight_train=None,
            **args,
        ):
            from sklearn.metrics import log_loss
            import time

            start = time.time()
            y_pred = estimator.predict_proba(X_val)
            pred_time = (time.time() - start) / len(X_val)
            val_loss = log_loss(y_val, y_pred, labels=labels, sample_weight=weight_val)
            y_pred = estimator.predict_proba(X_train)
            train_loss = log_loss(y_train, y_pred, labels=labels, sample_weight=weight_train)
            alpha = 0.5
            return val_loss * (1 + alpha) - alpha * train_loss, {
                "val_loss": val_loss,
                "train_loss": train_loss,
                "pred_time": pred_time,
            }
        ```
            task: A string of the task type, e.g.,
                'classification', 'regression', 'ts_forecast', 'rank',
                'seq-classification', 'seq-regression', 'summarization'
            n_jobs: An integer of the number of threads for training.
            log_file_name: A string of the log file name | default="". To disable logging,
                set it to be an empty string "".
            estimator_list: A list of strings for estimator names, or 'auto'
                e.g., ```['lgbm', 'xgboost', 'xgb_limitdepth', 'catboost', 'rf', 'extra_tree']```

            time_budget: A float number of the time budget in seconds.
                Use -1 if no time limit.
            max_iter: An integer of the maximal number of iterations.
            sample: A boolean of whether to sample the training data during
                search.
            ensemble: boolean or dict | default=False. Whether to perform
                ensemble after search. Can be a dict with keys 'passthrough'
                and 'final_estimator' to specify the passthrough and
                final_estimator in the stacker.
            eval_method: A string of resampling strategy, one of
                ['auto', 'cv', 'holdout'].
            split_ratio: A float of the valiation data percentage for holdout.
            n_splits: An integer of the number of folds for cross - validation.
            log_type: A string of the log type, one of
                ['better', 'all'].
                'better' only logs configs with better loss than previos iters
                'all' logs all the tried configs.
            model_history: A boolean of whether to keep the trained best
                model per estimator. Make sure memory is large enough if setting to True.
                Default value is False: best_model_for_estimator would return a
                untrained model for non-best learner.
            log_training_metric: A boolean of whether to log the training
                metric for each model.
            mem_thres: A float of the memory size constraint in bytes.
            pred_time_limit: A float of the prediction latency constraint in seconds.
                It refers to the average prediction time per row in validation data.
            train_time_limit: A float of the training time constraint in seconds.
            X_val: None or a numpy array or a pandas dataframe of validation data.
            y_val: None or a numpy array or a pandas series of validation labels.
            sample_weight_val: None or a numpy array of the sample weight of
                validation data of the same shape as y_val.
            groups_val: None or array-like | group labels (with matching length
                to y_val) or group counts (with sum equal to length of y_val)
                for validation data. Need to be consistent with groups.
            groups: None or array-like | Group labels (with matching length to
                y_train) or groups counts (with sum equal to length of y_train)
                for training data.
            verbose: int, default=3 | Controls the verbosity, higher means more
                messages.
            retrain_full: bool or str, default=True | whether to retrain the
                selected model on the full training data when using holdout.
                True - retrain only after search finishes; False - no retraining;
                'budget' - do best effort to retrain without violating the time
                budget.
            split_type: str or splitter object, default="auto" | the data split type.
                * A valid splitter object is an instance of a derived class of scikit-learn
                [KFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.KFold.html#sklearn.model_selection.KFold)
                and have ``split`` and ``get_n_splits`` methods with the same signatures.
                Set eval_method to "cv" to use the splitter object.
                * Valid str options depend on different tasks.
                For classification tasks, valid choices are
                    ["auto", 'stratified', 'uniform', 'time', 'group']. "auto" -> stratified.
                For regression tasks, valid choices are ["auto", 'uniform', 'time'].
                    "auto" -> uniform.
                For ts_forecast tasks, must be "auto" or 'time'.
                For ranking task, must be "auto" or 'group'.
            hpo_method: str, default="auto" | The hyperparameter
                optimization method. By default, CFO is used for sequential
                search and BlendSearch is used for parallel search.
                No need to set when using flaml's default search space or using
                a simple customized search space. When set to 'bs', BlendSearch
                is used. BlendSearch can be tried when the search space is
                complex, for example, containing multiple disjoint, discontinuous
                subspaces. When set to 'random', random search is used.
            starting_points: A dictionary to specify the starting hyperparameter
                config for the estimators.
                Keys are the name of the estimators, and values are the starting
                hyperparamter configurations for the corresponding estimators.
                The value can be a single hyperparamter configuration dict or a list
                of hyperparamter configuration dicts.
                In the following code example, we get starting_points from the
                `automl` object and use them in the `new_automl` object.
                e.g.,

        ```python
        from flaml import AutoML
        automl = AutoML()
        X_train, y_train = load_iris(return_X_y=True)
        automl.fit(X_train, y_train)
        starting_points = automl.best_config_per_estimator

        new_automl = AutoML()
        new_automl.fit(X_train, y_train, starting_points=starting_points)
        ```

            seed: int or None, default=None | The random seed for hpo.
            n_concurrent_trials: [Experimental] int, default=1 | The number of
                concurrent trials. For n_concurrent_trials > 1, installation of
                ray is required: `pip install flaml[ray]`.
            keep_search_state: boolean, default=False | Whether to keep data needed
                for model search after fit(). By default the state is deleted for
                space saving.
            early_stop: boolean, default=False | Whether to stop early if the
                search is considered to converge.
            append_log: boolean, default=False | Whetehr to directly append the log
                records to the input log file if it exists.
            auto_augment: boolean, default=True | Whether to automatically
                augment rare classes.
            min_sample_size: int, default=MIN_SAMPLE_TRAIN | the minimal sample
                size when sample=True.
            use_ray: boolean, default=False | Whether to use ray to run the training
                in separate processes. This can be used to prevent OOM for large
                datasets, but will incur more overhead in time. Only use it if
                you run into OOM failures.
            **fit_kwargs: Other key word arguments to pass to fit() function of
                the searched learners, such as sample_weight. Include:
                    period: int | forecast horizon for 'ts_forecast' task.
                    gpu_per_trial: float, default = 0 | A float of the number of gpus per trial,
                    only used by TransformersEstimator.
        """

        self._state._start_time_flag = self._start_time_flag = time.time()
        task = task or self._settings.get("task")
        self._estimator_type = "classifier" if task in CLASSIFICATION else "regressor"
        time_budget = time_budget or self._settings.get("time_budget")
        n_jobs = n_jobs or self._settings.get("n_jobs")
        gpu_per_trial = fit_kwargs.get("gpu_per_trial", 0)
        eval_method = eval_method or self._settings.get("eval_method")
        split_ratio = split_ratio or self._settings.get("split_ratio")
        n_splits = n_splits or self._settings.get("n_splits")
        auto_augment = (
            self._settings.get("auto_augment") if auto_augment is None else auto_augment
        )
        metric = metric or self._settings.get("metric")
        estimator_list = estimator_list or self._settings.get("estimator_list")
        log_file_name = (
            self._settings.get("log_file_name")
            if log_file_name is None
            else log_file_name
        )
        max_iter = self._settings.get("max_iter") if max_iter is None else max_iter
        sample = self._settings.get("sample") if sample is None else sample
        ensemble = self._settings.get("ensemble") if ensemble is None else ensemble
        log_type = log_type or self._settings.get("log_type")
        model_history = (
            self._settings.get("model_history")
            if model_history is None
            else model_history
        )
        log_training_metric = (
            self._settings.get("log_training_metric")
            if log_training_metric is None
            else log_training_metric
        )
        mem_thres = mem_thres or self._settings.get("mem_thres")
        pred_time_limit = pred_time_limit or self._settings.get("pred_time_limit")
        train_time_limit = train_time_limit or self._settings.get("train_time_limit")
        verbose = self._settings.get("verbose") if verbose is None else verbose
        retrain_full = (
            self._settings.get("retrain_full") if retrain_full is None else retrain_full
        )
        split_type = split_type or self._settings.get("split_type")
        hpo_method = hpo_method or self._settings.get("hpo_method")
        learner_selector = learner_selector or self._settings.get("learner_selector")
        starting_points = (
            self._settings.get("starting_points")
            if starting_points is None
            else starting_points
        )
        n_concurrent_trials = n_concurrent_trials or self._settings.get(
            "n_concurrent_trials"
        )
        keep_search_state = (
            self._settings.get("keep_search_state")
            if keep_search_state is None
            else keep_search_state
        )
        early_stop = (
            self._settings.get("early_stop") if early_stop is None else early_stop
        )
        append_log = (
            self._settings.get("append_log") if append_log is None else append_log
        )
        min_sample_size = min_sample_size or self._settings.get("min_sample_size")
        use_ray = self._settings.get("use_ray") if use_ray is None else use_ray

        self._state.task = TS_FORECAST if task == FORECAST else task
        self._state.log_training_metric = log_training_metric

        self._state.fit_kwargs = fit_kwargs
        self._state.weight_val = sample_weight_val

        self._validate_data(
            X_train, y_train, dataframe, label, X_val, y_val, groups_val, groups
        )
        self._search_states = {}  # key: estimator name; value: SearchState
        self._random = np.random.RandomState(RANDOM_SEED)
        self._seed = seed if seed is not None else 20
        self._learner_selector = learner_selector
        old_level = logger.getEffectiveLevel()
        self.verbose = verbose
        logger.setLevel(50 - verbose * 10)
        if not logger.handlers:
            # Add the console handler.
            _ch = logging.StreamHandler()
            _ch.setFormatter(logger_formatter)
            logger.addHandler(_ch)
        logger.info(f"task = {task}")
        self._decide_split_type(split_type)
        logger.info(f"Data split method: {self._split_type}")
        if eval_method == "auto" or self._state.X_val is not None:
            eval_method = self._decide_eval_method(time_budget)
        self._state.eval_method = eval_method
        logger.info("Evaluation method: {}".format(eval_method))

        self._state.n_jobs = n_jobs
        self._n_concurrent_trials = n_concurrent_trials
        self._early_stop = early_stop
        self._use_ray = use_ray or n_concurrent_trials > 1
        # use the following condition if we have an estimation of average_trial_time and average_trial_overhead
        # self._use_ray = use_ray or n_concurrent_trials > ( average_trail_time + average_trial_overhead) / (average_trial_time)
        if self._use_ray:
            import ray

            n_cpus = use_ray and ray.available_resources()["CPU"] or os.cpu_count()
            self._state.resources_per_trial = (
                # when using gpu, default cpu is 1 per job; otherwise, default cpu is n_cpus / n_concurrent_trials
                {"cpu": max(int(n_cpus / n_concurrent_trials), 1), "gpu": gpu_per_trial}
                if gpu_per_trial == 0
                else {"cpu": 1, "gpu": gpu_per_trial}
                if n_jobs < 0
                else {"cpu": n_jobs, "gpu": gpu_per_trial}
            )
        self._retrain_in_budget = retrain_full == "budget" and (
            eval_method == "holdout" and self._state.X_val is None
        )
        self._state.retrain_final = (
            retrain_full is True
            and eval_method == "holdout"
            and (self._state.X_val is None or self._use_ray)
            or eval_method == "cv"
            and (max_iter > 0 or retrain_full is True)
            or max_iter == 1
        )
        self._auto_augment = auto_augment
        self._min_sample_size = min_sample_size
        self._prepare_data(eval_method, split_ratio, n_splits)

        self._sample = (
            sample
            and task != "rank"
            and eval_method != "cv"
            and (
                self._min_sample_size * SAMPLE_MULTIPLY_FACTOR
                < self._state.data_size[0]
            )
        )
        if "auto" == metric:
            if "binary" in self._state.task:
                metric = "roc_auc"
            elif "multi" in self._state.task:
                metric = "log_loss"
            elif self._state.task == TS_FORECAST:
                metric = "mape"
            elif self._state.task == "rank":
                metric = "ndcg"
            elif _is_nlp_task(self._state.task):
                from .nlp.utils import load_default_huggingface_metric_for_task

                metric = load_default_huggingface_metric_for_task(self._state.task)
            else:
                metric = "r2"

        if _is_nlp_task(self._state.task):
            self._state.fit_kwargs["metric"] = metric
            self._state.fit_kwargs["use_ray"] = self._use_ray
            self._state.fit_kwargs["gpu_per_trial"] = gpu_per_trial

        self._state.metric = metric

        def is_to_reverse_metric(metric, task):
            if metric.startswith("ndcg"):
                return True, f"1-{metric}"
            if metric in [
                "r2",
                "accuracy",
                "roc_auc",
                "roc_auc_ovr",
                "roc_auc_ovo",
                "f1",
                "ap",
                "micro_f1",
                "macro_f1",
            ]:
                return True, f"1-{metric}"
            if _is_nlp_task(task):
                from .ml import huggingface_metric_to_mode

                if (
                    metric in huggingface_metric_to_mode
                    and huggingface_metric_to_mode[metric] == "max"
                ):
                    return True, f"-{metric}"
            return False, None

        if isinstance(metric, str):
            is_reverse, reverse_metric = is_to_reverse_metric(metric, task)
            if is_reverse:
                error_metric = reverse_metric
            else:
                error_metric = metric
        else:
            error_metric = "customized metric"
        logger.info(f"Minimizing error metric: {error_metric}")

        if "auto" == estimator_list:
            if self._state.task == "rank":
                estimator_list = ["lgbm", "xgboost", "xgb_limitdepth"]
            elif _is_nlp_task(self._state.task):
                estimator_list = ["transformer"]
            else:
                try:
                    import catboost

                    estimator_list = [
                        "lgbm",
                        "rf",
                        "catboost",
                        "xgboost",
                        "extra_tree",
                        "xgb_limitdepth",
                    ]
                except ImportError:
                    estimator_list = [
                        "lgbm",
                        "rf",
                        "xgboost",
                        "extra_tree",
                        "xgb_limitdepth",
                    ]
                if TS_FORECAST == self._state.task:
                    # catboost is removed because it has a `name` parameter, making it incompatible with hcrystalball
                    if "catboost" in estimator_list:
                        estimator_list.remove("catboost")
                    try:
                        import prophet

                        estimator_list += ["prophet", "arima", "sarimax"]
                    except ImportError:
                        estimator_list += ["arima", "sarimax"]
                elif "regression" != self._state.task:
                    estimator_list += ["lrl1"]

        for estimator_name in estimator_list:
            if estimator_name not in self._state.learner_classes:
                self.add_learner(
                    estimator_name,
                    get_estimator_class(self._state.task, estimator_name),
                )
        # set up learner search space
        for estimator_name in estimator_list:
            estimator_class = self._state.learner_classes[estimator_name]
            estimator_class.init()
            self._search_states[estimator_name] = SearchState(
                learner_class=estimator_class,
                data_size=self._state.data_size,
                task=self._state.task,
                starting_point=starting_points.get(estimator_name),
                period=self._state.fit_kwargs.get("period"),
            )
        logger.info("List of ML learners in AutoML Run: {}".format(estimator_list))
        self.estimator_list = estimator_list
        self._state.time_budget = time_budget if time_budget > 0 else 1e10
        self._active_estimators = estimator_list.copy()
        self._ensemble = ensemble
        self._max_iter = max_iter
        self._mem_thres = mem_thres
        self._pred_time_limit = pred_time_limit
        self._state.train_time_limit = train_time_limit
        self._log_type = log_type
        self.split_ratio = split_ratio
        self._state.model_history = model_history
        self._hpo_method = (
            hpo_method
            if hpo_method != "auto"
            else (
                "bs"
                if n_concurrent_trials > 1 or self._use_ray and len(estimator_list) > 1
                else "cfo"
            )
        )
        if log_file_name:
            with training_log_writer(log_file_name, append_log) as save_helper:
                self._training_log = save_helper
                self._search()
        else:
            self._training_log = None
            self._search()
        if self._best_estimator:
            logger.info("fit succeeded")
            logger.info(
                f"Time taken to find the best model: {self._time_taken_best_iter}"
            )
            if (
                self._hpo_method in ("cfo", "bs")
                and (self._time_taken_best_iter >= self._state.time_budget * 0.7)
                and not all(
                    state.search_alg and state.search_alg.searcher.is_ls_ever_converged
                    for state in self._search_states.values()
                )
            ):
                logger.warning(
                    "Time taken to find the best model is {0:.0f}% of the "
                    "provided time budget and not all estimators' hyperparameter "
                    "search converged. Consider increasing the time budget.".format(
                        self._time_taken_best_iter / self._state.time_budget * 100
                    )
                )

        if not keep_search_state:
            # release space
            del self._X_train_all, self._y_train_all, self._state.kf
            del self._state.X_train, self._state.X_train_all, self._state.X_val
            del self._state.y_train, self._state.y_train_all, self._state.y_val
            del self._sample_weight_full, self._state.fit_kwargs
            del self._state.groups, self._state.groups_all, self._state.groups_val
        logger.setLevel(old_level)

    def _search_parallel(self):
        try:
            from ray import __version__ as ray_version

            assert ray_version >= "1.0.0"
            import ray
            from ray.tune.suggest import ConcurrencyLimiter
        except (ImportError, AssertionError):
            raise ImportError(
                "n_concurrent_trial>1 or use_ray=True requires installation of ray. "
                "Please run pip install flaml[ray]"
            )
        if self._hpo_method in ("cfo", "grid"):
            from flaml import CFO as SearchAlgo
        elif "bs" == self._hpo_method:
            from flaml import BlendSearch as SearchAlgo
        elif "random" == self._hpo_method:
            from ray.tune.suggest import BasicVariantGenerator as SearchAlgo
            from ray.tune.sample import Domain
        else:
            raise NotImplementedError(
                f"hpo_method={self._hpo_method} is not recognized. "
                "'auto', 'cfo' and 'bs' are supported."
            )
        space = self.search_space
        if self._hpo_method == "random":
            # Any point in points_to_evaluate must consist of hyperparamters
            # that are tunable, which can be identified by checking whether
            # the corresponding value in the search space is an instance of
            # the 'Domain' class from flaml or ray.tune
            points_to_evaluate = self.points_to_evaluate.copy()
            to_del = []
            for k, v in space.items():
                if not isinstance(v, Domain):
                    to_del.append(k)
            for k in to_del:
                for p in points_to_evaluate:
                    if k in p:
                        del p[k]
            search_alg = SearchAlgo(
                max_concurrent=self._n_concurrent_trials,
                points_to_evaluate=points_to_evaluate,
            )
        else:
            self._state.time_from_start = time.time() - self._start_time_flag
            time_left = self._state.time_budget - self._state.time_from_start
            search_alg = SearchAlgo(
                metric="val_loss",
                space=space,
                low_cost_partial_config=self.low_cost_partial_config,
                points_to_evaluate=self.points_to_evaluate,
                cat_hp_cost=self.cat_hp_cost,
                resource_attr=self.resource_attr,
                min_resource=self.min_resource,
                max_resource=self.max_resource,
                config_constraints=[
                    (partial(size, self._state), "<=", self._mem_thres)
                ],
                metric_constraints=self.metric_constraints,
                seed=self._seed,
                time_budget_s=time_left,
            )
            search_alg = ConcurrencyLimiter(search_alg, self._n_concurrent_trials)
        resources_per_trial = self._state.resources_per_trial
        analysis = ray.tune.run(
            self.trainable,
            search_alg=search_alg,
            config=space,
            metric="val_loss",
            mode="min",
            resources_per_trial=resources_per_trial,
            time_budget_s=self._state.time_budget,
            num_samples=self._max_iter,
            verbose=max(self.verbose - 2, 0),
            raise_on_failed_trial=False,
            keep_checkpoints_num=1,
            checkpoint_score_attr="min-val_loss",
        )
        # logger.info([trial.last_result for trial in analysis.trials])
        trials = sorted(
            (
                trial
                for trial in analysis.trials
                if trial.last_result
                and trial.last_result.get("wall_clock_time") is not None
            ),
            key=lambda x: x.last_result["wall_clock_time"],
        )
        for self._track_iter, trial in enumerate(trials):
            result = trial.last_result
            better = False
            if result:
                config = result["config"]
                estimator = config.get("ml", config)["learner"]
                search_state = self._search_states[estimator]
                search_state.update(result, 0)
                wall_time = result.get("wall_clock_time")
                if wall_time is not None:
                    self._state.time_from_start = wall_time
                self._iter_per_learner[estimator] += 1
                if search_state.sample_size == self._state.data_size[0]:
                    if not self._fullsize_reached:
                        self._fullsize_reached = True
                if search_state.best_loss < self._state.best_loss:
                    self._state.best_loss = search_state.best_loss
                    self._best_estimator = estimator
                    self._config_history[self._track_iter] = (
                        self._best_estimator,
                        config,
                        self._time_taken_best_iter,
                    )
                    self._trained_estimator = search_state.trained_estimator
                    self._best_iteration = self._track_iter
                    self._time_taken_best_iter = self._state.time_from_start
                    better = True
                    self._search_states[estimator].best_config = config
                if better or self._log_type == "all":
                    self._log_trial(search_state, estimator)

    def _log_trial(self, search_state, estimator):
        if self._training_log:
            self._training_log.append(
                self._iter_per_learner[estimator],
                search_state.metric_for_logging,
                search_state.trial_time,
                self._state.time_from_start,
                search_state.val_loss,
                search_state.config,
                estimator,
                search_state.sample_size,
            )
        if mlflow is not None and mlflow.active_run():
            with mlflow.start_run(nested=True):
                mlflow.log_metric("iter_counter", self._track_iter)
                if "intermediate_results" in search_state.metric_for_logging:
                    for each_entry in search_state.metric_for_logging[
                        "intermediate_results"
                    ]:
                        with mlflow.start_run(nested=True):
                            mlflow.log_metrics(each_entry)
                            mlflow.log_metric(
                                "iter_counter", self._iter_per_learner[estimator]
                            )
                    del search_state.metric_for_logging["intermediate_results"]
                mlflow.log_metrics(search_state.metric_for_logging)
                mlflow.log_metric("trial_time", search_state.trial_time)
                mlflow.log_metric("wall_clock_time", self._state.time_from_start)
                mlflow.log_metric("validation_loss", search_state.val_loss)
                mlflow.log_param("config", search_state.config)
                mlflow.log_param("learner", estimator)
                mlflow.log_param("sample_size", search_state.sample_size)
                mlflow.log_metric("best_validation_loss", search_state.best_loss)
                mlflow.log_param("best_config", search_state.best_config)
                mlflow.log_param("best_learner", self._best_estimator)

    def _search_sequential(self):
        try:
            from ray import __version__ as ray_version

            assert ray_version >= "1.0.0"
            from ray.tune.suggest import ConcurrencyLimiter
        except (ImportError, AssertionError):
            from .searcher.suggestion import ConcurrencyLimiter
        if self._hpo_method in ("cfo", "grid"):
            from flaml import CFO as SearchAlgo
        elif "optuna" == self._hpo_method:
            try:
                from ray import __version__ as ray_version

                assert ray_version >= "1.0.0"
                from ray.tune.suggest.optuna import OptunaSearch as SearchAlgo
            except (ImportError, AssertionError):
                from .searcher.suggestion import OptunaSearch as SearchAlgo
        elif "bs" == self._hpo_method:
            from flaml import BlendSearch as SearchAlgo
        elif "random" == self._hpo_method:
            from flaml.searcher import RandomSearch as SearchAlgo
        elif "cfocat" == self._hpo_method:
            from flaml.searcher.cfo_cat import CFOCat as SearchAlgo
        else:
            raise NotImplementedError(
                f"hpo_method={self._hpo_method} is not recognized. "
                "'cfo' and 'bs' are supported."
            )

        est_retrain_time = next_trial_time = 0
        best_config_sig = None
        better = True  # whether we find a better model in one trial
        if self._ensemble:
            self.best_model = {}
        if self._max_iter < 2 and self.estimator_list and self._state.retrain_final:
            # when max_iter is 1, no need to search
            # TODO: otherwise, need to make sure SearchStates.init_config is inside search space
            self._max_iter = 0
            self._best_estimator = estimator = self.estimator_list[0]
            self._selected = state = self._search_states[estimator]
            state.best_config_sample_size = self._state.data_size[0]
            state.best_config = (
                state.init_config
                if isinstance(state.init_config, dict)
                else state.init_config[0]
            )
        for self._track_iter in range(self._max_iter):
            if self._estimator_index is None:
                estimator = self._active_estimators[0]
            else:
                estimator = self._select_estimator(self._active_estimators)
                if not estimator:
                    break
            logger.info(f"iteration {self._track_iter}, current learner {estimator}")
            search_state = self._search_states[estimator]
            self._state.time_from_start = time.time() - self._start_time_flag
            time_left = self._state.time_budget - self._state.time_from_start
            budget_left = (
                time_left
                if not self._retrain_in_budget
                or better
                or (not self.best_estimator)
                or self._search_states[self.best_estimator].sample_size
                < self._state.data_size[0]
                else time_left - est_retrain_time
            )
            if not search_state.search_alg:
                search_state.training_function = partial(
                    AutoMLState._compute_with_config_base, self._state, estimator
                )
                search_space = search_state.search_space
                if self._sample:
                    resource_attr = "FLAML_sample_size"
                    min_resource = self._min_sample_size
                    max_resource = self._state.data_size[0]
                else:
                    resource_attr = min_resource = max_resource = None
                learner_class = self._state.learner_classes.get(estimator)
                if "grid" == self._hpo_method:  # for synthetic exp only
                    points_to_evaluate = []
                    space = search_space
                    keys = list(space.keys())
                    domain0, domain1 = space[keys[0]], space[keys[1]]
                    for x1 in range(domain0.lower, domain0.upper + 1):
                        for x2 in range(domain1.lower, domain1.upper + 1):
                            points_to_evaluate.append(
                                {
                                    keys[0]: x1,
                                    keys[1]: x2,
                                }
                            )
                    self._max_iter_per_learner = len(points_to_evaluate)
                    low_cost_partial_config = None
                else:
                    points_to_evaluate = (
                        search_state.init_config
                        if isinstance(search_state.init_config, list)
                        else [search_state.init_config]
                    )
                    low_cost_partial_config = search_state.low_cost_partial_config
                if self._hpo_method in ("bs", "cfo", "grid", "cfocat", "random"):
                    algo = SearchAlgo(
                        metric="val_loss",
                        mode="min",
                        space=search_space,
                        points_to_evaluate=points_to_evaluate,
                        low_cost_partial_config=low_cost_partial_config,
                        cat_hp_cost=search_state.cat_hp_cost,
                        resource_attr=resource_attr,
                        min_resource=min_resource,
                        max_resource=max_resource,
                        config_constraints=[
                            (learner_class.size, "<=", self._mem_thres)
                        ],
                        metric_constraints=self.metric_constraints,
                        seed=self._seed,
                    )
                else:
                    algo = SearchAlgo(
                        metric="val_loss",
                        mode="min",
                        space=search_space,
                        points_to_evaluate=[
                            p for p in points_to_evaluate if len(p) == len(search_space)
                        ],
                    )
                search_state.search_alg = ConcurrencyLimiter(algo, max_concurrent=1)
                # search_state.search_alg = algo
            else:
                search_space = None
                if self._hpo_method in ("bs", "cfo", "cfocat"):
                    search_state.search_alg.searcher.set_search_properties(
                        metric=None,
                        mode=None,
                        setting={
                            "metric_target": self._state.best_loss,
                        },
                    )
            start_run_time = time.time()
            analysis = tune.run(
                search_state.training_function,
                search_alg=search_state.search_alg,
                time_budget_s=min(budget_left, self._state.train_time_limit),
                verbose=max(self.verbose - 3, 0),
                use_ray=False,
            )
            time_used = time.time() - start_run_time
            better = False
            if analysis.trials:
                result = analysis.trials[-1].last_result
                search_state.update(result, time_used=time_used)
                if self._estimator_index is None:
                    # update init eci estimate
                    eci_base = search_state.init_eci
                    self._eci.append(search_state.estimated_cost4improvement)
                    for e in self.estimator_list[1:]:
                        self._eci.append(
                            self._search_states[e].init_eci / eci_base * self._eci[0]
                        )
                    self._estimator_index = 0
                    min_budget = max(10 * self._eci[0], sum(self._eci))
                    max_budget = 10000 * self._eci[0]
                    if search_state.sample_size:
                        ratio = search_state.data_size[0] / search_state.sample_size
                        min_budget *= ratio
                        max_budget *= ratio
                    logger.info(
                        f"Estimated sufficient time budget={max_budget:.0f}s."
                        f" Estimated necessary time budget={min_budget:.0f}s."
                    )
                wall_time = result.get("wall_clock_time")
                if wall_time is not None:
                    self._state.time_from_start = wall_time
                # logger.info(f"{self._search_states[estimator].sample_size}, {data_size}")
                if search_state.sample_size == self._state.data_size[0]:
                    self._iter_per_learner_fullsize[estimator] += 1
                    self._fullsize_reached = True
                self._iter_per_learner[estimator] += 1
                if search_state.best_loss < self._state.best_loss:
                    best_config_sig = estimator + search_state.get_hist_config_sig(
                        self.data_size_full, search_state.best_config
                    )
                    self._state.best_loss = search_state.best_loss
                    self._best_estimator = estimator
                    est_retrain_time = (
                        search_state.est_retrain_time(self.data_size_full)
                        if (best_config_sig not in self._retrained_config)
                        else 0
                    )
                    self._config_history[self._track_iter] = (
                        estimator,
                        search_state.best_config,
                        self._state.time_from_start,
                    )
                    if self._trained_estimator:
                        self._trained_estimator.cleanup()
                        del self._trained_estimator
                        self._trained_estimator = None
                    if not self._state.retrain_final:
                        self._trained_estimator = search_state.trained_estimator
                    self._best_iteration = self._track_iter
                    self._time_taken_best_iter = self._state.time_from_start
                    better = True
                    next_trial_time = search_state.time2eval_best
                if (
                    search_state.trained_estimator
                    and not self._state.model_history
                    and search_state.trained_estimator != self._trained_estimator
                ):
                    search_state.trained_estimator.cleanup()
                if better or self._log_type == "all":
                    self._log_trial(search_state, estimator)

                logger.info(
                    " at {:.1f}s,\testimator {}'s best error={:.4f},\tbest estimator {}'s best error={:.4f}".format(
                        self._state.time_from_start,
                        estimator,
                        search_state.best_loss,
                        self._best_estimator,
                        self._state.best_loss,
                    )
                )
                if (
                    self._hpo_method in ("cfo", "bs")
                    and all(
                        state.search_alg
                        and state.search_alg.searcher.is_ls_ever_converged
                        for state in self._search_states.values()
                    )
                    and (
                        self._state.time_from_start
                        > self._warn_threshold * self._time_taken_best_iter
                    )
                ):
                    logger.warning(
                        "All estimator hyperparameters local search has "
                        "converged at least once, and the total search time "
                        f"exceeds {self._warn_threshold} times the time taken "
                        "to find the best model."
                    )
                    if self._early_stop:
                        logger.warning("Stopping search as early_stop is set to True.")
                        break
                    self._warn_threshold *= 10
            else:
                logger.info(f"stop trying learner {estimator}")
                if self._estimator_index is not None:
                    self._active_estimators.remove(estimator)
                    self._estimator_index -= 1
                search_state.search_alg.searcher._is_ls_ever_converged = True
            if (
                self._retrain_in_budget
                and best_config_sig
                and est_retrain_time
                and not better
                and self._search_states[self._best_estimator].sample_size
                == self._state.data_size[0]
                and (
                    est_retrain_time
                    <= self._state.time_budget - self._state.time_from_start
                    <= est_retrain_time + next_trial_time
                )
            ):
                state = self._search_states[self._best_estimator]
                self._trained_estimator, retrain_time = self._state._train_with_config(
                    self._best_estimator,
                    state.best_config,
                    self.data_size_full,
                )
                logger.info(
                    "retrain {} for {:.1f}s".format(self._best_estimator, retrain_time)
                )
                self._retrained_config[
                    best_config_sig
                ] = state.best_config_train_time = retrain_time
                est_retrain_time = 0
            self._state.time_from_start = time.time() - self._start_time_flag
            if (
                self._state.time_from_start >= self._state.time_budget
                or not self._active_estimators
            ):
                break
            if self._ensemble and self._best_estimator:
                time_left = self._state.time_budget - self._state.time_from_start
                time_ensemble = self._search_states[self._best_estimator].time2eval_best
                if time_left < time_ensemble < 2 * time_left:
                    break

    def _search(self):
        # initialize the search_states
        self._eci = []
        self._state.best_loss = float("+inf")
        self._state.time_from_start = 0
        self._estimator_index = None
        self._best_iteration = 0
        self._time_taken_best_iter = 0
        self._config_history = {}
        self._max_iter_per_learner = 10000
        self._iter_per_learner = dict([(e, 0) for e in self.estimator_list])
        self._iter_per_learner_fullsize = dict([(e, 0) for e in self.estimator_list])
        self._fullsize_reached = False
        self._trained_estimator = None
        self._best_estimator = None
        self._retrained_config = {}
        self._warn_threshold = 10
        self._selected = None
        self.modelcount = 0

        if not self._use_ray:
            self._search_sequential()
        else:
            self._search_parallel()
        # Add a checkpoint for the current best config to the log.
        if self._training_log:
            self._training_log.checkpoint()
        if self._best_estimator:
            self._selected = self._search_states[self._best_estimator]
            self.modelcount = sum(
                search_state.total_iter for search_state in self._search_states.values()
            )
            if self._trained_estimator:
                logger.info(f"selected model: {self._trained_estimator.model}")
            estimators = []
            if self._ensemble and self._state.task in (
                "binary",
                "multi",
                "regression",
            ):
                search_states = list(
                    x for x in self._search_states.items() if x[1].best_config
                )
                search_states.sort(key=lambda x: x[1].best_loss)
                estimators = [
                    (
                        x[0],
                        x[1].learner_class(
                            task=self._state.task,
                            n_jobs=self._state.n_jobs,
                            **x[1].best_config,
                        ),
                    )
                    for x in search_states[:2]
                ]
                estimators += [
                    (
                        x[0],
                        x[1].learner_class(
                            task=self._state.task,
                            n_jobs=self._state.n_jobs,
                            **x[1].best_config,
                        ),
                    )
                    for x in search_states[2:]
                    if x[1].best_loss < 4 * self._selected.best_loss
                ]
                logger.info(estimators)
            if len(estimators) > 1:
                if self._state.task in CLASSIFICATION:
                    from sklearn.ensemble import StackingClassifier as Stacker
                else:
                    from sklearn.ensemble import StackingRegressor as Stacker
                if isinstance(self._ensemble, dict):
                    final_estimator = self._ensemble.get(
                        "final_estimator", self._trained_estimator
                    )
                    passthrough = self._ensemble.get("passthrough", True)
                else:
                    final_estimator = self._trained_estimator
                    passthrough = True
                stacker = Stacker(
                    estimators,
                    final_estimator,
                    n_jobs=self._state.n_jobs,
                    passthrough=passthrough,
                )
                if self._sample_weight_full is not None:
                    self._state.fit_kwargs["sample_weight"] = self._sample_weight_full
                for e in estimators:
                    e[1].__class__.init()
                try:
                    stacker.fit(
                        self._X_train_all, self._y_train_all, **self._state.fit_kwargs
                    )
                    logger.info(f"ensemble: {stacker}")
                    self._trained_estimator = stacker
                    self._trained_estimator.model = stacker
                except ValueError as e:
                    if passthrough:
                        logger.warning(
                            "Using passthrough=False for ensemble because the data contain categorical features."
                        )
                        stacker = Stacker(
                            estimators,
                            final_estimator,
                            n_jobs=self._state.n_jobs,
                            passthrough=False,
                        )
                        stacker.fit(
                            self._X_train_all,
                            self._y_train_all,
                            **self._state.fit_kwargs,
                        )
                        logger.info(f"ensemble: {stacker}")
                        self._trained_estimator = stacker
                        self._trained_estimator.model = stacker
                    else:
                        raise e
            elif self._state.retrain_final:
                # reset time budget for retraining
                if self._max_iter > 1:
                    self._state.time_from_start -= self._state.time_budget
                if (
                    self._state.task == TS_FORECAST
                    or self._trained_estimator is None
                    or self._trained_estimator.model is None
                    or (
                        self._state.time_budget - self._state.time_from_start
                        > self._selected.est_retrain_time(self.data_size_full)
                        and self._selected.best_config_sample_size
                        == self._state.data_size[0]
                    )
                ):
                    state = self._search_states[self._best_estimator]
                    (
                        self._trained_estimator,
                        retrain_time,
                    ) = self._state._train_with_config(
                        self._best_estimator,
                        state.best_config,
                        self.data_size_full,
                    )
                    logger.info(
                        "retrain {} for {:.1f}s".format(
                            self._best_estimator, retrain_time
                        )
                    )
                    state.best_config_train_time = retrain_time
                    if self._trained_estimator:
                        logger.info(f"retrained model: {self._trained_estimator.model}")
                else:
                    logger.info("not retraining because the time budget is too small.")

    def __del__(self):
        if (
            hasattr(self, "_trained_estimator")
            and self._trained_estimator
            and hasattr(self._trained_estimator, "cleanup")
        ):
            self._trained_estimator.cleanup()
            del self._trained_estimator

    def _select_estimator(self, estimator_list):
        if self._learner_selector == "roundrobin":
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
                if (
                    self._search_states[estimator].time2eval_best
                    > self._state.time_budget - self._state.time_from_start
                    or self._iter_per_learner_fullsize[estimator]
                    >= self._max_iter_per_learner
                ):
                    inv.append(0)
                    continue
                estimated_cost = search_state.estimated_cost4improvement
                if search_state.sample_size < self._state.data_size[0]:
                    estimated_cost = min(
                        estimated_cost,
                        search_state.time2eval_best
                        * min(
                            SAMPLE_MULTIPLY_FACTOR,
                            self._state.data_size[0] / search_state.sample_size,
                        ),
                    )
                gap = search_state.best_loss - self._state.best_loss
                if gap > 0 and not self._ensemble:
                    delta_loss = (
                        search_state.best_loss_old - search_state.best_loss
                    ) or search_state.best_loss
                    delta_time = (
                        search_state.total_time_used - search_state.time_best_found_old
                    ) or 1e-10
                    speed = delta_loss / delta_time
                    if speed:
                        estimated_cost = max(2 * gap / speed, estimated_cost)
                estimated_cost = estimated_cost or 1e-9
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
