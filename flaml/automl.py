# !
#  * Copyright (c) FLAML authors. All rights reserved.
#  * Licensed under the MIT License. See LICENSE file in the
#  * project root for license information.
import time
import os
from typing import Callable, Optional, List, Union, Any
import inspect
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
    TS_FORECASTREGRESSION,
    REGRESSION,
    _is_nlp_task,
    NLG_TASKS,
)
from . import tune
from .training_log import training_log_reader, training_log_writer
from flaml.default.suggest import suggest_learner

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

    def valid_starting_point_one_dim(self, value_one_dim, domain_one_dim):
        from .tune.space import sample

        """
            For each hp in the starting point, check the following 3 conditions:
            (1) If the type of the starting point does not match the required type in search space, return false
            (2) If the starting point is not in the required search space, return false
            (3) If the search space is a value instead of domain, and the value is not equal to the starting point
            Notice (2) include the case starting point not in user specified search space custom_hp
        """
        if isinstance(domain_one_dim, sample.Domain):
            renamed_type = list(
                inspect.signature(domain_one_dim.is_valid).parameters.values()
            )[0].annotation
            type_match = renamed_type == Any or isinstance(value_one_dim, renamed_type)
            if not (type_match and domain_one_dim.is_valid(value_one_dim)):
                return False
        elif value_one_dim != domain_one_dim:
            return False
        return True

    def valid_starting_point(self, starting_point, search_space):
        return any(
            [
                self.valid_starting_point_one_dim(
                    value, search_space[name].get("domain")
                )
                for name, value in starting_point.items()
            ]
        )

    def __init__(
        self,
        learner_class,
        data_size,
        task,
        starting_point=None,
        period=None,
        custom_hp=None,
        max_iter=None,
    ):
        self.init_eci = learner_class.cost_relative2lgbm()
        self._search_space_domain = {}
        self.init_config = {}
        self.low_cost_partial_config = {}
        self.cat_hp_cost = {}
        self.data_size = data_size
        self.ls_ever_converged = False
        self.learner_class = learner_class
        if task in TS_FORECAST:
            search_space = learner_class.search_space(
                data_size=data_size, task=task, pred_horizon=period
            )
        else:
            search_space = learner_class.search_space(data_size=data_size, task=task)

        if custom_hp is not None:
            search_space.update(custom_hp)

        if (
            isinstance(starting_point, dict)
            and max_iter
            > 1  # If the number of starting point is larger than max iter, avoid the checking
            and not self.valid_starting_point(starting_point, search_space)
        ):
            logger.warning(
                "Starting point {} removed because it is outside of the search space".format(
                    starting_point
                )
            )
            starting_point = None
        elif isinstance(starting_point, list) and max_iter > len(
            starting_point
        ):  # If the number of starting point is larger than max iter, avoid the checking
            starting_point_len = len(starting_point)
            starting_point = [
                x for x in starting_point if self.valid_starting_point(x, search_space)
            ]
            if starting_point_len > len(starting_point):
                logger.warning(
                    "Starting points outside of the search space are removed. "
                    f"Remaining starting points: {starting_point}"
                )
            starting_point = starting_point or None

        for name, space in search_space.items():
            assert (
                "domain" in space
            ), f"{name}'s domain is missing in the search space spec {space}"
            if space["domain"] is None:
                # don't search this hp
                continue
            self._search_space_domain[name] = space["domain"]

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
            elif (
                not isinstance(starting_point, list)
                and "init_value" in space
                and self.valid_starting_point_one_dim(
                    space["init_value"], space["domain"]
                )
            ):  # If starting point is list, no need to check the validity of self.init_config w.r.t search space
                self.init_config[name] = space[
                    "init_value"
                ]  # If starting_point is list, no need to assign value to self.init_config here

        if isinstance(starting_point, list):
            self.init_config = starting_point

        self._hp_names = list(self._search_space_domain.keys())
        self.search_alg = None
        self.best_config = None
        self.best_result = None
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
            self.best_result = result
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
            weight = self.fit_kwargs.get(
                "sample_weight"
            )  # NOTE: _prepare_sample_train_data is before
            if weight is not None:
                sampled_weight = weight[:sample_size]
            if self.groups is not None:
                groups = self.groups[:sample_size]
        else:
            sampled_X_train = self.X_train_all
            sampled_y_train = self.y_train_all
            if (
                "sample_weight" in self.fit_kwargs
            ):  # NOTE: _prepare_sample_train_data is before
                sampled_weight = self.sample_weight_all
            if self.groups is not None:
                groups = self.groups_all
        return sampled_X_train, sampled_y_train, sampled_weight, groups

    @staticmethod
    def _compute_with_config_base(config_w_resource, state, estimator):
        if "FLAML_sample_size" in config_w_resource:
            sample_size = int(config_w_resource["FLAML_sample_size"])
        else:
            sample_size = state.data_size[0]

        this_estimator_kwargs = state.fit_kwargs_by_estimator.get(
            estimator
        ).copy()  # NOTE: _compute_with_config_base is after
        (
            sampled_X_train,
            sampled_y_train,
            sampled_weight,
            groups,
        ) = state._prepare_sample_train_data(sample_size)
        if sampled_weight is not None:
            weight = this_estimator_kwargs["sample_weight"]
            this_estimator_kwargs["sample_weight"] = sampled_weight
        if groups is not None:
            this_estimator_kwargs["groups"] = groups
        config = config_w_resource.copy()
        if "FLAML_sample_size" in config:
            del config["FLAML_sample_size"]
        budget = (
            None
            if state.time_budget is None
            else state.time_budget - state.time_from_start
            if sample_size == state.data_size[0]
            else (state.time_budget - state.time_from_start)
            / 2
            * sample_size
            / state.data_size[0]
        )

        (
            trained_estimator,
            val_loss,
            metric_for_logging,
            _,
            pred_time,
        ) = compute_estimator(
            sampled_X_train,
            sampled_y_train,
            state.X_val,
            state.y_val,
            state.weight_val,
            state.groups_val,
            state.train_time_limit
            if budget is None
            else min(budget, state.train_time_limit),
            state.kf,
            config,
            state.task,
            estimator,
            state.eval_method,
            state.metric,
            state.best_loss,
            state.n_jobs,
            state.learner_classes.get(estimator),
            state.log_training_metric,
            this_estimator_kwargs,
        )
        if state.retrain_final and not state.model_history:
            trained_estimator.cleanup()

        result = {
            "pred_time": pred_time,
            "wall_clock_time": time.time() - state._start_time_flag,
            "metric_for_logging": metric_for_logging,
            "val_loss": val_loss,
            "trained_estimator": trained_estimator,
        }
        if sampled_weight is not None:
            this_estimator_kwargs["sample_weight"] = weight
        tune.report(**result)
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

        this_estimator_kwargs = self.fit_kwargs_by_estimator.get(
            estimator
        ).copy()  # NOTE: _train_with_config is after
        (
            sampled_X_train,
            sampled_y_train,
            sampled_weight,
            groups,
        ) = self._prepare_sample_train_data(sample_size)
        if sampled_weight is not None:
            weight = this_estimator_kwargs[
                "sample_weight"
            ]  # NOTE: _train_with_config is after
            this_estimator_kwargs[
                "sample_weight"
            ] = sampled_weight  # NOTE: _train_with_config is after
        if groups is not None:
            this_estimator_kwargs[
                "groups"
            ] = groups  # NOTE: _train_with_config is after

        budget = (
            None
            if self.time_budget is None
            else self.time_budget - self.time_from_start
        )

        estimator, train_time = train_estimator(
            X_train=sampled_X_train,
            y_train=sampled_y_train,
            config_dic=config,
            task=self.task,
            estimator_name=estimator,
            n_jobs=self.n_jobs,
            estimator_class=self.learner_classes.get(estimator),
            budget=budget,
            fit_kwargs=this_estimator_kwargs,  # NOTE: _train_with_config is after
            eval_metric=self.metric if hasattr(self, "metric") else "train_time",
        )

        if sampled_weight is not None:
            this_estimator_kwargs[
                "sample_weight"
            ] = weight  # NOTE: _train_with_config is after

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
            *args,
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
            n_jobs: An integer of the number of threads for training | default=-1.
                Use all available resources when n_jobs == -1.
            log_file_name: A string of the log file name | default="". To disable logging,
                set it to be an empty string "".
            estimator_list: A list of strings for estimator names, or 'auto'.
                e.g., ```['lgbm', 'xgboost', 'xgb_limitdepth', 'catboost', 'rf', 'extra_tree']```.
            time_budget: A float number of the time budget in seconds.
                Use -1 if no time limit.
            max_iter: An integer of the maximal number of iterations.
            sample: A boolean of whether to sample the training data during
                search.
            ensemble: boolean or dict | default=False. Whether to perform
                ensemble after search. Can be a dict with keys 'passthrough'
                and 'final_estimator' to specify the passthrough and
                final_estimator in the stacker. The dict can also contain
                'n_jobs' as the key to specify the number of jobs for the stacker.
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
            starting_points: A dictionary or a str to specify the starting hyperparameter
                config for the estimators | default="static".
                If str:
                    - if "data", use data-dependent defaults;
                    - if "data:path" use data-dependent defaults which are stored at path;
                    - if "static", use data-independent defaults.
                If dict, keys are the name of the estimators, and values are the starting
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
                concurrent trials. When n_concurrent_trials > 1, flaml performes
                [parallel tuning](https://microsoft.github.io/FLAML/docs/Use-Cases/Task-Oriented-AutoML#parallel-tuning)
                and installation of ray is required: `pip install flaml[ray]`.
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
            metric_constraints: list, default=[] | The list of metric constraints.
                Each element in this list is a 3-tuple, which shall be expressed
                in the following format: the first element of the 3-tuple is the name of the
                metric, the second element is the inequality sign chosen from ">=" and "<=",
                and the third element is the constraint value. E.g., `('val_loss', '<=', 0.1)`.
                Note that all the metric names in metric_constraints need to be reported via
                the metrics_to_log dictionary returned by a customized metric function.
                The customized metric function shall be provided via the `metric` key word
                argument of the fit() function or the automl constructor.
                Find an example in the 4th constraint type in this [doc](https://microsoft.github.io/FLAML/docs/Use-Cases/Task-Oriented-AutoML#constraint).
                If `pred_time_limit` is provided as one of keyword arguments to fit() function or
                the automl constructor, flaml will automatically (and under the hood)
                add it as an additional element in the metric_constraints. Essentially 'pred_time_limit'
                specifies a constraint about the prediction latency constraint in seconds.
            custom_hp: dict, default=None | The custom search space specified by user
                Each key is the estimator name, each value is a dict of the custom search space for that estimator. Notice the
                domain of the custom search space can either be a value of a sample.Domain object.
                e.g.,

        ```python
        custom_hp = {
             "transformer_ms": {
                 "model_path": {
                     "domain": "albert-base-v2",
                 },
                 "learning_rate": {
                     "domain": tune.choice([1e-4, 1e-5]),
                 }
             }
         }
        ```
            fit_kwargs_by_estimator: dict, default=None | The user specified keywords arguments, grouped by estimator name.
                e.g.,

        ```python
        fit_kwargs_by_estimator = {
            "transformer": {
                "output_dir": "test/data/output/",
                "ckpt_per_epoch": 1,
                "fp16": False,
            }
        }
        ```

        """
        self._track_iter = 0
        self._state = AutoMLState()
        self._state.learner_classes = {}
        self._settings = settings
        # no budget by default
        settings["time_budget"] = settings.get("time_budget", -1)
        settings["task"] = settings.get("task", "classification")
        settings["n_jobs"] = settings.get("n_jobs", -1)
        settings["eval_method"] = settings.get("eval_method", "auto")
        settings["split_ratio"] = settings.get("split_ratio", SPLIT_RATIO)
        settings["n_splits"] = settings.get("n_splits", N_SPLITS)
        settings["auto_augment"] = settings.get("auto_augment", True)
        settings["metric"] = settings.get("metric", "auto")
        settings["estimator_list"] = settings.get("estimator_list", "auto")
        settings["log_file_name"] = settings.get("log_file_name", "")
        settings["max_iter"] = settings.get("max_iter")  # no budget by default
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
        settings["starting_points"] = settings.get("starting_points", "static")
        settings["n_concurrent_trials"] = settings.get("n_concurrent_trials", 1)
        settings["keep_search_state"] = settings.get("keep_search_state", False)
        settings["early_stop"] = settings.get("early_stop", False)
        settings["append_log"] = settings.get("append_log", False)
        settings["min_sample_size"] = settings.get("min_sample_size", MIN_SAMPLE_TRAIN)
        settings["use_ray"] = settings.get("use_ray", False)
        settings["metric_constraints"] = settings.get("metric_constraints", [])
        settings["fit_kwargs_by_estimator"] = settings.get(
            "fit_kwargs_by_estimator", {}
        )
        settings["custom_hp"] = settings.get("custom_hp", {})

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
    def best_result(self):
        """Result dictionary for model trained with the best config."""
        state = self._search_states.get(self._best_estimator)
        return state and getattr(state, "best_result", None)

    @property
    def metrics_for_best_config(self):
        """Returns a float of the best loss, and a dictionary of the auxiliary metrics to log
        associated with the best config. These two objects correspond to the returned
        objects by the customized metric function for the config with the best loss."""
        state = self._search_states.get(self._best_estimator)
        return self._state.best_loss, state and getattr(state, "best_result", {}).get(
            "metric_for_logging"
        )

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
        """A numpy array of shape (n_classes,) for class labels."""
        attr = getattr(self, "_label_transformer", None)
        if attr:
            return attr.classes_
        attr = getattr(self, "_trained_estimator", None)
        if attr:
            return attr.classes_
        return None

    @property
    def n_features_in_(self):
        return self._trained_estimator.n_features_in_

    @property
    def time_to_find_best_model(self) -> float:
        """Time taken to find best model in seconds."""
        return self.__dict__.get("_time_taken_best_iter")

    def score(self, X: pd.DataFrame, y: pd.Series, **kwargs):
        estimator = getattr(self, "_trained_estimator", None)
        if estimator is None:
            logger.warning(
                "No estimator is trained. Please run fit with enough budget."
            )
            return None
        X = self._preprocess(X)
        if self._label_transformer:
            y = self._label_transformer.transform(y)
        return estimator.score(X, y, **kwargs)

    def predict(
        self,
        X: Union[np.array, pd.DataFrame, List[str], List[List[str]]],
        **pred_kwargs,
    ):
        """Predict label from features.

        Args:
            X: A numpy array of featurized instances, shape n * m,
                or for ts_forecast tasks:
                    a pandas dataframe with the first column containing
                    timestamp values (datetime type) or an integer n for
                    the predict steps (only valid when the estimator is
                    arima or sarimax). Other columns in the dataframe
                    are assumed to be exogenous variables (categorical
                    or numeric).
            **pred_kwargs: Other key word arguments to pass to predict() function of
                the searched learners, such as per_device_eval_batch_size.

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
        y_pred = estimator.predict(X, **pred_kwargs)
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

    def predict_proba(self, X, **pred_kwargs):
        """Predict the probability of each class from features, only works for
        classification problems.

        Args:
            X: A numpy array of featurized instances, shape n * m.
            **pred_kwargs: Other key word arguments to pass to predict_proba() function of
                the searched learners, such as per_device_eval_batch_size.

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
        proba = self._trained_estimator.predict_proba(X, **pred_kwargs)
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
        if self._state.task in TS_FORECAST:
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
            if self._state.task in TS_FORECAST:
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
            if self._state.task in TS_FORECAST:
                dataframe = self._validate_ts_data(dataframe)
            X = dataframe.drop(columns=label)
            self._nrow, self._ndim = X.shape
            y = dataframe[label]
        else:
            raise ValueError("either X_train+y_train or dataframe+label are required")

        # check the validity of input dimensions for NLP tasks, so need to check _is_nlp_task not estimator
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

        self._sample_weight_full = self._state.fit_kwargs.get(
            "sample_weight"
        )  # NOTE: _validate_data is before,
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
            and self._state.fit_kwargs.get("sample_weight")
            is None  # NOTE: _prepare_data is before
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
                self._state.fit_kwargs[
                    "sample_weight"
                ] = self._state.sample_weight_all  # NOTE: _prepare_data is before
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
                if self._state.task in TS_FORECAST:
                    num_samples = X_train_all.shape[0]
                    period = self._state.fit_kwargs[
                        "period"
                    ]  # NOTE: _prepare_data is before
                    assert (
                        period < num_samples
                    ), f"period={period}>#examples={num_samples}"
                    split_idx = num_samples - period
                    X_train = X_train_all[:split_idx]
                    y_train = y_train_all[:split_idx]
                    X_val = X_train_all[split_idx:]
                    y_val = y_train_all[split_idx:]
                else:
                    if (
                        "sample_weight" in self._state.fit_kwargs
                    ):  # NOTE: _prepare_data is before
                        (
                            X_train,
                            X_val,
                            y_train,
                            y_val,
                            self._state.fit_kwargs[
                                "sample_weight"
                            ],  # NOTE: _prepare_data is before
                            self._state.weight_val,
                        ) = train_test_split(
                            X_train_all,
                            y_train_all,
                            self._state.fit_kwargs[
                                "sample_weight"
                            ],  # NOTE: _prepare_data is before
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
                if (
                    "sample_weight" in self._state.fit_kwargs
                ):  # NOTE: _prepare_data is before
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
                        self._state.fit_kwargs["sample_weight"][
                            rest
                        ],  # NOTE: _prepare_data is before
                        test_size=split_ratio,
                        random_state=RANDOM_SEED,
                    )
                    weight1 = self._state.fit_kwargs["sample_weight"][
                        first
                    ]  # NOTE: _prepare_data is before
                    self._state.weight_val = concat(weight1, weight_val)
                    self._state.fit_kwargs[
                        "sample_weight"
                    ] = concat(  # NOTE: _prepare_data is before
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
                if (
                    "sample_weight" in self._state.fit_kwargs
                ):  # NOTE: _prepare_data is before
                    (
                        X_train,
                        X_val,
                        y_train,
                        y_val,
                        self._state.fit_kwargs[
                            "sample_weight"
                        ],  # NOTE: _prepare_data is before
                        self._state.weight_val,
                    ) = train_test_split(
                        X_train_all,
                        y_train_all,
                        self._state.fit_kwargs[
                            "sample_weight"
                        ],  # NOTE: _prepare_data is before
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
            if self._state.task in TS_FORECAST:
                period = self._state.fit_kwargs[
                    "period"
                ]  # NOTE: _prepare_data is before
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
                'binary', 'multiclass', 'regression', 'ts_forecast', 'rank'.

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
            eval_metric="train_time",
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
        custom_hp=None,
        fit_kwargs_by_estimator=None,
        **fit_kwargs,
    ):
        """Retrain from log file.

        Args:
            log_file_name: A string of the log file name.
            X_train: A numpy array or dataframe of training data in shape n*m.
                For ts_forecast tasks, the first column of X_train
                must be the timestamp column (datetime type). Other
                columns in the dataframe are assumed to be exogenous
                variables (categorical or numeric).
            y_train: A numpy array or series of labels in shape n*1.
            dataframe: A dataframe of training data including label column.
                For ts_forecast tasks, dataframe must be specified and should
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
            n_jobs: An integer of the number of threads for training | default=-1.
                Use all available resources when n_jobs == -1.
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
            custom_hp: dict, default=None | The custom search space specified by user
                Each key is the estimator name, each value is a dict of the custom search space for that estimator. Notice the
                domain of the custom search space can either be a value or a sample.Domain object.

        ```python
        custom_hp = {
            "transformer_ms": {
                "model_path": {
                    "domain": "albert-base-v2",
                },
                "learning_rate": {
                    "domain": tune.choice([1e-4, 1e-5]),
                }
            }
        }
        ```
            fit_kwargs_by_estimator: dict, default=None | The user specified keywords arguments, grouped by estimator name.
                e.g.,

        ```python
        fit_kwargs_by_estimator = {
            "transformer": {
                "output_dir": "test/data/output/",
                "ckpt_per_epoch": 1,
                "fp16": False,
            }
        }
        ```

            **fit_kwargs: Other key word arguments to pass to fit() function of
                the searched learners, such as sample_weight. Include:
                    period: int | forecast horizon for ts_forecast tasks.
                    gpu_per_trial: float, default = 0 | A float of the number of gpus per trial,
                    only used by TransformersEstimator and XGBoostSklearnEstimator.
        """
        task = task or self._settings.get("task")
        eval_method = eval_method or self._settings.get("eval_method")
        split_ratio = split_ratio or self._settings.get("split_ratio")
        n_splits = n_splits or self._settings.get("n_splits")
        split_type = split_type or self._settings.get("split_type")
        auto_augment = (
            self._settings.get("auto_augment") if auto_augment is None else auto_augment
        )
        self._state.task = task
        self._estimator_type = "classifier" if task in CLASSIFICATION else "regressor"

        self._state.fit_kwargs = fit_kwargs
        self._state.custom_hp = custom_hp or self._settings.get("custom_hp")
        self._state.fit_kwargs_by_estimator = (
            fit_kwargs_by_estimator or self._settings.get("fit_kwargs_by_estimator")
        )
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

        this_estimator_kwargs = self._state.fit_kwargs_by_estimator.get(best_estimator)
        if this_estimator_kwargs:
            this_estimator_kwargs = (
                this_estimator_kwargs.copy()
            )  # make another shallow copy of the value (a dict obj), so user's fit_kwargs_by_estimator won't be updated
            this_estimator_kwargs.update(self._state.fit_kwargs)
            self._state.fit_kwargs_by_estimator[best_estimator] = this_estimator_kwargs
        else:
            self._state.fit_kwargs_by_estimator[best_estimator] = self._state.fit_kwargs

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
            {
                "cpu": max(1, os.cpu_count() >> 1),
                "gpu": fit_kwargs.get("gpu_per_trial", 0),
            }
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
        elif self._state.task in TS_FORECAST:
            assert split_type in ["auto", "time"]
            self._split_type = "time"

            assert isinstance(
                self._state.fit_kwargs.get("period"),
                int,  # NOTE: _decide_split_type is before
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

    def pickle(self, output_file_name):
        import pickle

        estimator_to_training_function = {}
        for estimator in self.estimator_list:
            search_state = self._search_states[estimator]
            if hasattr(search_state, "training_function"):
                estimator_to_training_function[
                    estimator
                ] = search_state.training_function
                del search_state.training_function

        with open(output_file_name, "wb") as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

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
                if self._use_ray is not False:
                    from ray.tune import with_parameters

                    search_state.training_function = with_parameters(
                        AutoMLState._compute_with_config_base,
                        state=self._state,
                        estimator=estimator,
                    )
                else:
                    search_state.training_function = partial(
                        AutoMLState._compute_with_config_base,
                        state=self._state,
                        estimator=estimator,
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
        return self._metric_constraints

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
        metric_constraints=None,
        custom_hp=None,
        fit_kwargs_by_estimator=None,
        **fit_kwargs,
    ):
        """Find a model for a given task.

        Args:
            X_train: A numpy array or a pandas dataframe of training data in
                shape (n, m). For ts_forecast tasks, the first column of X_train
                must be the timestamp column (datetime type). Other columns in
                the dataframe are assumed to be exogenous variables (categorical or numeric).
                When using ray, X_train can be a ray.ObjectRef.
            y_train: A numpy array or a pandas series of labels in shape (n, ).
            dataframe: A dataframe of training data including label column.
                For ts_forecast tasks, dataframe must be specified and must have
                at least two columns, timestamp and label, where the first
                column is the timestamp column (datetime type). Other columns in
                the dataframe are assumed to be exogenous variables (categorical or numeric).
                When using ray, dataframe can be a ray.ObjectRef.
            label: A str of the label column name for, e.g., 'label';
                Note: If X_train and y_train are provided,
                dataframe and label are ignored;
                If not, dataframe and label must be provided.
            metric: A string of the metric name or a function,
                e.g., 'accuracy', 'roc_auc', 'roc_auc_ovr', 'roc_auc_ovo',
                'f1', 'micro_f1', 'macro_f1', 'log_loss', 'mae', 'mse', 'r2',
                'mape'. Default is 'auto'.
                If passing a customized metric function, the function needs to
                have the following signature:

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
            *args,
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
                'classification', 'regression', 'ts_forecast_regression',
                'ts_forecast_classification', 'rank', 'seq-classification',
                'seq-regression', 'summarization'.
            n_jobs: An integer of the number of threads for training | default=-1.
                Use all available resources when n_jobs == -1.
            log_file_name: A string of the log file name | default="". To disable logging,
                set it to be an empty string "".
            estimator_list: A list of strings for estimator names, or 'auto'.
                e.g., ```['lgbm', 'xgboost', 'xgb_limitdepth', 'catboost', 'rf', 'extra_tree']```.
            time_budget: A float number of the time budget in seconds.
                Use -1 if no time limit.
            max_iter: An integer of the maximal number of iterations.
                NOTE: when both time_budget and max_iter are unspecified,
                only one model will be trained per estimator.
            sample: A boolean of whether to sample the training data during
                search.
            ensemble: boolean or dict | default=False. Whether to perform
                ensemble after search. Can be a dict with keys 'passthrough'
                and 'final_estimator' to specify the passthrough and
                final_estimator in the stacker. The dict can also contain
                'n_jobs' as the key to specify the number of jobs for the stacker.
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
            starting_points: A dictionary or a str to specify the starting hyperparameter
                config for the estimators | default="data".
                If str:
                    - if "data", use data-dependent defaults;
                    - if "data:path" use data-dependent defaults which are stored at path;
                    - if "static", use data-independent defaults.
                If dict, keys are the name of the estimators, and values are the starting
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
                concurrent trials. When n_concurrent_trials > 1, flaml performes
                [parallel tuning](https://microsoft.github.io/FLAML/docs/Use-Cases/Task-Oriented-AutoML#parallel-tuning)
                and installation of ray is required: `pip install flaml[ray]`.
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
            use_ray: boolean or dict
                If boolean: default=False | Whether to use ray to run the training
                in separate processes. This can be used to prevent OOM for large
                datasets, but will incur more overhead in time.
            metric_constraints: list, default=[] | The list of metric constraints.
                Each element in this list is a 3-tuple, which shall be expressed
                in the following format: the first element of the 3-tuple is the name of the
                metric, the second element is the inequality sign chosen from ">=" and "<=",
                and the third element is the constraint value. E.g., `('precision', '>=', 0.9)`.
                Note that all the metric names in metric_constraints need to be reported via
                the metrics_to_log dictionary returned by a customized metric function.
                The customized metric function shall be provided via the `metric` key word argument
                of the fit() function or the automl constructor.
                Find examples in this [test](https://github.com/microsoft/FLAML/tree/main/test/automl/test_constraints.py).
                If `pred_time_limit` is provided as one of keyword arguments to fit() function or
                the automl constructor, flaml will automatically (and under the hood)
                add it as an additional element in the metric_constraints. Essentially 'pred_time_limit'
                specifies a constraint about the prediction latency constraint in seconds.
            custom_hp: dict, default=None | The custom search space specified by user
                Each key is the estimator name, each value is a dict of the custom search space for that estimator. Notice the
                domain of the custom search space can either be a value of a sample.Domain object.

        ```python
        custom_hp = {
            "transformer_ms": {
                "model_path": {
                    "domain": "albert-base-v2",
                },
                "learning_rate": {
                    "domain": tune.choice([1e-4, 1e-5]),
                }
            }
        }
        ```

        fit_kwargs_by_estimator: dict, default=None | The user specified keywords arguments, grouped by estimator name.
                For TransformersEstimator, available fit_kwargs can be found from
                [flaml/nlp/training_args.py:TrainingArgumentsForAuto](https://microsoft.github.io/FLAML/docs/reference/nlp/huggingface/training_args).
                e.g.,

        ```python
        fit_kwargs_by_estimator = {
            "transformer": {
                "output_dir": "test/data/output/",
                "ckpt_per_epoch": 1,
                "fp16": False,
            }
        }
        ```

            **fit_kwargs: Other key word arguments to pass to fit() function of
                the searched learners, such as sample_weight. Include:
                    period: int | forecast horizon for ts_forecast tasks.
                    gpu_per_trial: float, default = 0 | A float of the number of gpus per trial,
                    only used by TransformersEstimator and XGBoostSklearnEstimator.
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
        sample_is_none = sample is None
        if sample_is_none:
            sample = self._settings.get("sample")
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
        self._metric_constraints = metric_constraints or self._settings.get(
            "metric_constraints"
        )
        if np.isfinite(pred_time_limit):
            self._metric_constraints.append(("pred_time", "<=", pred_time_limit))
        verbose = self._settings.get("verbose") if verbose is None else verbose
        retrain_full = (
            self._settings.get("retrain_full") if retrain_full is None else retrain_full
        )
        split_type = split_type or self._settings.get("split_type")
        hpo_method = hpo_method or self._settings.get("hpo_method")
        learner_selector = learner_selector or self._settings.get("learner_selector")
        no_starting_points = starting_points is None
        if no_starting_points:
            starting_points = self._settings.get("starting_points")
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
        # no search budget is provided?
        no_budget = time_budget == -1 and max_iter is None and not early_stop
        append_log = (
            self._settings.get("append_log") if append_log is None else append_log
        )
        min_sample_size = min_sample_size or self._settings.get("min_sample_size")
        use_ray = self._settings.get("use_ray") if use_ray is None else use_ray
        self._state.n_jobs = n_jobs
        self._n_concurrent_trials = n_concurrent_trials
        self._early_stop = early_stop
        self._use_ray = use_ray or n_concurrent_trials > 1
        # use the following condition if we have an estimation of average_trial_time and average_trial_overhead
        # self._use_ray = use_ray or n_concurrent_trials > ( average_trail_time + average_trial_overhead) / (average_trial_time)
        if self._use_ray is not False:
            import ray

            n_cpus = (
                ray.is_initialized()
                and ray.available_resources()["CPU"]
                or os.cpu_count()
            )

            self._state.resources_per_trial = (
                # when using gpu, default cpu is 1 per job; otherwise, default cpu is n_cpus / n_concurrent_trials
                (
                    {
                        "cpu": max(int((n_cpus - 2) / 2 / n_concurrent_trials), 1),
                        "gpu": gpu_per_trial,
                    }
                    if gpu_per_trial == 0
                    else {"cpu": 1, "gpu": gpu_per_trial}
                )
                if n_jobs < 0
                else {"cpu": n_jobs, "gpu": gpu_per_trial}
            )

            if isinstance(X_train, ray.ObjectRef):
                X_train = ray.get(X_train)
            elif isinstance(dataframe, ray.ObjectRef):
                dataframe = ray.get(dataframe)

        self._state.task = task
        self._state.log_training_metric = log_training_metric

        self._state.fit_kwargs = fit_kwargs
        custom_hp = custom_hp or self._settings.get("custom_hp")
        fit_kwargs_by_estimator = fit_kwargs_by_estimator or self._settings.get(
            "fit_kwargs_by_estimator"
        )
        self._state.fit_kwargs_by_estimator = (
            fit_kwargs_by_estimator.copy()
        )  # shallow copy of fit_kwargs_by_estimator
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

        self._retrain_in_budget = retrain_full == "budget" and (
            eval_method == "holdout" and self._state.X_val is None
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
            if _is_nlp_task(self._state.task):
                from .nlp.utils import load_default_huggingface_metric_for_task

                metric = load_default_huggingface_metric_for_task(self._state.task)
            elif "binary" in self._state.task:
                metric = "roc_auc"
            elif "multiclass" in self._state.task:
                metric = "log_loss"
            elif self._state.task in TS_FORECAST:
                metric = "mape"
            elif self._state.task == "rank":
                metric = "ndcg"
            else:
                metric = "r2"

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
                if self._state.task in TS_FORECAST:
                    # catboost is removed because it has a `name` parameter, making it incompatible with hcrystalball
                    if "catboost" in estimator_list:
                        estimator_list.remove("catboost")
                    if self._state.task in TS_FORECASTREGRESSION:
                        try:
                            import prophet

                            estimator_list += ["prophet", "arima", "sarimax"]
                        except ImportError:
                            estimator_list += ["arima", "sarimax"]
                elif "regression" != self._state.task:
                    estimator_list += ["lrl1"]
        # When no search budget is specified
        if no_budget:
            max_iter = len(estimator_list)
            self._learner_selector = "roundrobin"
            if sample_is_none:
                self._sample = False
            if no_starting_points:
                starting_points = "data"
            logger.warning(
                "No search budget is provided via time_budget or max_iter."
                " Training only one model per estimator."
                " To tune hyperparameters for each estimator,"
                " please provide budget either via time_budget or max_iter."
            )
        elif max_iter is None:
            # set to a large number
            max_iter = 1000000
        self._state.retrain_final = (
            retrain_full is True
            and eval_method == "holdout"
            and (X_val is None or self._use_ray is not False)
            or eval_method == "cv"
            and (max_iter > 0 or retrain_full is True)
            or max_iter == 1
        )
        # add custom learner
        for estimator_name in estimator_list:
            if estimator_name not in self._state.learner_classes:
                self.add_learner(
                    estimator_name,
                    get_estimator_class(self._state.task, estimator_name),
                )
        # set up learner search space
        if isinstance(starting_points, str) and starting_points.startswith("data"):
            from flaml.default import suggest_config

            location = starting_points[5:]
            starting_points = {}
            for estimator_name in estimator_list:
                try:
                    configs = suggest_config(
                        self._state.task,
                        self._X_train_all,
                        self._y_train_all,
                        estimator_name,
                        location,
                        k=1,
                    )
                    starting_points[estimator_name] = [
                        x["hyperparameters"] for x in configs
                    ]
                except FileNotFoundError:
                    pass
            try:
                learner = suggest_learner(
                    self._state.task,
                    self._X_train_all,
                    self._y_train_all,
                    estimator_list=estimator_list,
                    location=location,
                )
                if learner != estimator_list[0]:
                    estimator_list.remove(learner)
                    estimator_list.insert(0, learner)
            except FileNotFoundError:
                pass

        starting_points = {} if starting_points == "static" else starting_points

        for estimator_name in estimator_list:
            estimator_class = self._state.learner_classes[estimator_name]
            estimator_class.init()
            this_estimator_kwargs = self._state.fit_kwargs_by_estimator.get(
                estimator_name
            )
            if this_estimator_kwargs:
                # make another shallow copy of the value (a dict obj), so user's fit_kwargs_by_estimator won't be updated
                this_estimator_kwargs = this_estimator_kwargs.copy()
                this_estimator_kwargs.update(
                    self._state.fit_kwargs
                )  # update the shallow copy
                self._state.fit_kwargs_by_estimator[
                    estimator_name
                ] = this_estimator_kwargs  # set self._state.fit_kwargs_by_estimator[estimator_name] to the update, so only self._state.fit_kwargs_by_estimator will be updated
            else:
                self._state.fit_kwargs_by_estimator[
                    estimator_name
                ] = self._state.fit_kwargs

            self._search_states[estimator_name] = SearchState(
                learner_class=estimator_class,
                data_size=self._state.data_size,
                task=self._state.task,
                starting_point=starting_points.get(estimator_name),
                period=self._state.fit_kwargs.get("period"),  # NOTE: this is after
                custom_hp=custom_hp and custom_hp.get(estimator_name),
                max_iter=max_iter,
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
                if n_concurrent_trials > 1
                or self._use_ray is not False
                and len(estimator_list) > 1
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
            del (
                self._sample_weight_full,
                self._state.fit_kwargs_by_estimator,
                self._state.fit_kwargs,
            )  # NOTE: this is after
            del self._state.groups, self._state.groups_all, self._state.groups_val
        logger.setLevel(old_level)

    def _search_parallel(self):
        try:
            from ray import __version__ as ray_version

            assert ray_version >= "1.10.0"
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
        elif "optuna" == self._hpo_method:
            try:
                from ray import __version__ as ray_version

                assert ray_version >= "1.10.0"
                from ray.tune.suggest.optuna import OptunaSearch as SearchAlgo
            except (ImportError, AssertionError):
                from .searcher.suggestion import OptunaSearch as SearchAlgo
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
            if self._hpo_method != "optuna":
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
            else:
                # if self._hpo_method is bo, sometimes the search space and the initial config dimension do not match
                # need to remove the extra keys from the search space to be consistent with the initial config
                converted_space = SearchAlgo.convert_search_space(space)

                removed_keys = set(space.keys()).difference(converted_space.keys())
                new_points_to_evaluate = []
                for idx in range(len(self.points_to_evaluate)):
                    r = self.points_to_evaluate[idx].copy()
                    for each_key in removed_keys:
                        r.pop(each_key)
                    new_points_to_evaluate.append(r)

                search_alg = SearchAlgo(
                    metric="val_loss",
                    mode="min",
                    points_to_evaluate=[
                        p
                        for p in new_points_to_evaluate
                        if len(p) == len(converted_space)
                    ],
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
            **self._use_ray if isinstance(self._use_ray, dict) else {},
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

            assert ray_version >= "1.10.0"
            from ray.tune.suggest import ConcurrencyLimiter
        except (ImportError, AssertionError):
            from .searcher.suggestion import ConcurrencyLimiter
        if self._hpo_method in ("cfo", "grid"):
            from flaml import CFO as SearchAlgo
        elif "optuna" == self._hpo_method:
            try:
                from ray import __version__ as ray_version

                assert ray_version >= "1.10.0"
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
                    AutoMLState._compute_with_config_base,
                    state=self._state,
                    estimator=estimator,
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
                    # if self._hpo_method is bo, sometimes the search space and the initial config dimension do not match
                    # need to remove the extra keys from the search space to be consistent with the initial config
                    converted_space = SearchAlgo.convert_search_space(search_space)
                    removed_keys = set(search_space.keys()).difference(
                        converted_space.keys()
                    )
                    new_points_to_evaluate = []
                    for idx in range(len(points_to_evaluate)):
                        r = points_to_evaluate[idx].copy()
                        for each_key in removed_keys:
                            r.pop(each_key)
                        new_points_to_evaluate.append(r)
                    points_to_evaluate = new_points_to_evaluate

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
        if self._max_iter < 2 and self.estimator_list and self._state.retrain_final:
            # when max_iter is 1, no need to search
            # TODO: otherwise, need to make sure SearchStates.init_config is inside search space
            self.modelcount = self._max_iter
            self._max_iter = 0
            self._best_estimator = estimator = self.estimator_list[0]
            self._selected = state = self._search_states[estimator]
            state.best_config_sample_size = self._state.data_size[0]
            state.best_config = (
                state.init_config
                if isinstance(state.init_config, dict)
                else state.init_config[0]
            )
        elif self._use_ray is False:
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
                "multiclass",
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
                if self._use_ray is not False:
                    import ray

                    n_cpus = (
                        ray.is_initialized()
                        and ray.available_resources()["CPU"]
                        or os.cpu_count()
                    )
                else:
                    n_cpus = os.cpu_count()
                ensemble_n_jobs = (
                    -self._state.n_jobs  # maximize total parallelization degree
                    if abs(self._state.n_jobs)
                    == 1  # 1 and -1 correspond to min/max parallelization
                    else max(1, int(n_cpus / 2 / self._state.n_jobs))
                    # the total degree of parallelization = parallelization degree per estimator * parallelization degree of ensemble
                )
                if isinstance(self._ensemble, dict):
                    final_estimator = self._ensemble.get(
                        "final_estimator", self._trained_estimator
                    )
                    passthrough = self._ensemble.get("passthrough", True)
                    ensemble_n_jobs = self._ensemble.get("n_jobs", ensemble_n_jobs)
                else:
                    final_estimator = self._trained_estimator
                    passthrough = True
                stacker = Stacker(
                    estimators,
                    final_estimator,
                    n_jobs=ensemble_n_jobs,
                    passthrough=passthrough,
                )
                sample_weight_dict = (
                    (self._sample_weight_full is not None)
                    and {"sample_weight": self._sample_weight_full}
                    or {}
                )
                for e in estimators:
                    e[1].__class__.init()
                import joblib

                try:
                    stacker.fit(
                        self._X_train_all,
                        self._y_train_all,
                        **sample_weight_dict,  # NOTE: _search is after
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
                            **sample_weight_dict,  # NOTE: _search is after
                        )
                        logger.info(f"ensemble: {stacker}")
                        self._trained_estimator = stacker
                        self._trained_estimator.model = stacker
                    else:
                        raise e
                except joblib.externals.loky.process_executor.TerminatedWorkerError:
                    logger.error(
                        "No enough memory to build the ensemble."
                        " Please try increasing available RAM, decreasing n_jobs for ensemble, or disabling ensemble."
                    )
            elif self._state.retrain_final:
                # reset time budget for retraining
                if self._max_iter > 1:
                    self._state.time_from_start -= self._state.time_budget
                if (
                    self._state.task in TS_FORECAST
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
