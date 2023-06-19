import inspect
import copy
import time
from typing import Any, Optional
import numpy as np
from flaml import tune
from flaml.automl.logger import logger
from flaml.automl.ml import compute_estimator, train_estimator
from flaml.automl.time_series.ts_data import TimeSeriesDataset
from flaml.automl.spark import psDataFrame, psSeries, DataFrame, Series


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
        from flaml.tune.space import sample

        """
            For each hp in the starting point, check the following 3 conditions:
            (1) If the type of the starting point does not match the required type in search space, return false
            (2) If the starting point is not in the required search space, return false
            (3) If the search space is a value instead of domain, and the value is not equal to the starting point
            Notice (2) include the case starting point not in user specified search space custom_hp
        """
        if isinstance(domain_one_dim, sample.Domain):
            renamed_type = list(inspect.signature(domain_one_dim.is_valid).parameters.values())[0].annotation
            type_match = (
                renamed_type == Any
                or isinstance(value_one_dim, renamed_type)
                or isinstance(value_one_dim, int)
                and renamed_type is float
            )
            if not (type_match and domain_one_dim.is_valid(value_one_dim)):
                return False
        elif value_one_dim != domain_one_dim:
            return False
        return True

    def valid_starting_point(self, starting_point, search_space):
        return all(
            self.valid_starting_point_one_dim(value, search_space[name].get("domain"))
            for name, value in starting_point.items()
            if name != "FLAML_sample_size"
        )

    def __init__(
        self,
        learner_class,
        data,
        task,
        starting_point=None,
        period=None,
        custom_hp=None,
        max_iter=None,
        budget=None,
    ):
        self.init_eci = learner_class.cost_relative2lgbm() if budget >= 0 else 1
        self._search_space_domain = {}
        self.init_config = None
        self.low_cost_partial_config = {}
        self.cat_hp_cost = {}

        self.ls_ever_converged = False
        self.learner_class = learner_class
        self._budget = budget

        if task.is_ts_forecast():
            data_size = data.train_data.shape
            search_space = learner_class.search_space(data=data, task=task, pred_horizon=period)
        else:
            data_size = data.shape
            search_space = learner_class.search_space(data_size=data_size, task=task)
        self.data_size = data_size

        if custom_hp is not None:
            search_space.update(custom_hp)

        if isinstance(starting_point, dict):
            starting_point = AutoMLState.sanitize(starting_point)
            if max_iter > 1 and not self.valid_starting_point(starting_point, search_space):
                # If the number of iterations is larger than 1, remove invalid point
                logger.warning(
                    "Starting point {} removed because it is outside of the search space".format(starting_point)
                )
                starting_point = None
        elif isinstance(starting_point, list):
            starting_point = [AutoMLState.sanitize(x) for x in starting_point]
            if max_iter > len(starting_point):
                # If the number of starting points is no smaller than max iter, avoid the checking
                starting_point_len = len(starting_point)
                starting_point = [x for x in starting_point if self.valid_starting_point(x, search_space)]
                if starting_point_len > len(starting_point):
                    logger.warning(
                        "Starting points outside of the search space are removed. "
                        f"Remaining starting points for {learner_class}: {starting_point}"
                    )
                starting_point = starting_point or None

        for name, space in search_space.items():
            assert "domain" in space, f"{name}'s domain is missing in the search space spec {space}"
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
            if isinstance(starting_point, dict) and starting_point.get(name) is not None:
                if self.init_config is None:
                    self.init_config = {}
                self.init_config[name] = starting_point[name]
            elif (
                not isinstance(starting_point, list)
                and "init_value" in space
                and self.valid_starting_point_one_dim(space["init_value"], space["domain"])
            ):
                if self.init_config is None:
                    self.init_config = {}
                self.init_config[name] = space["init_value"]

        if isinstance(starting_point, list):
            self.init_config = starting_point
        else:
            self.init_config = [] if self.init_config is None else [self.init_config]

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
                and trained_estimator.params.get(trained_estimator.ITER_HP)
            )
            if n_iter:
                if "ml" in config:
                    config["ml"][trained_estimator.ITER_HP] = n_iter
                else:
                    config[trained_estimator.ITER_HP] = n_iter
        else:
            obj, time2eval, trained_estimator = np.inf, 0.0, None
            metric_for_logging = config = None
        self.trial_time = time2eval
        self.total_time_used += time_used if self._budget >= 0 else 1
        self.total_iter += 1

        if self.base_eci is None:
            self.base_eci = time_used
        if (obj is not None) and (obj < self.best_loss):
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
            if self.trained_estimator and trained_estimator and self.trained_estimator != trained_estimator:
                self.trained_estimator.cleanup()
            if trained_estimator:
                self.trained_estimator = trained_estimator
        elif trained_estimator:
            trained_estimator.cleanup()
        self.metric_for_logging = metric_for_logging
        self.val_loss, self.config = obj, config

    def get_hist_config_sig(self, sample_size, config):
        config_values = tuple([config[k] for k in self._hp_names if k in config])
        config_sig = str(sample_size) + "_" + str(config_values)
        return config_sig

    def est_retrain_time(self, retrain_sample_size):
        assert self.best_config_sample_size is not None, "need to first get best_config_sample_size"
        return self.time2eval_best * retrain_sample_size / self.best_config_sample_size


class AutoMLState:
    def prepare_sample_train_data(self, sample_size: int):
        sampled_weight = groups = None
        if sample_size <= self.data_size[0]:
            if isinstance(self.X_train, TimeSeriesDataset):
                sampled_X_train = copy.copy(self.X_train)
                sampled_X_train.train_data = self.X_train.train_data.iloc[-sample_size:]
                sampled_y_train = None
            else:
                if isinstance(self.X_train, (DataFrame, psDataFrame)):
                    sampled_X_train = self.X_train.iloc[:sample_size]
                else:
                    sampled_X_train = self.X_train[:sample_size]
                if isinstance(self.y_train, (Series, psSeries)):
                    sampled_y_train = self.y_train.iloc[:sample_size]
                else:
                    sampled_y_train = self.y_train[:sample_size]
            weight = self.fit_kwargs.get(
                "sample_weight"
            )  # NOTE: _prepare_sample_train_data is before kwargs is updated to fit_kwargs_by_estimator
            if weight is not None:
                sampled_weight = (
                    weight.iloc[:sample_size] if isinstance(weight, (Series, psSeries)) else weight[:sample_size]
                )
            if self.groups is not None:
                groups = (
                    self.groups.iloc[:sample_size]
                    if isinstance(self.groups, (Series, psSeries))
                    else self.groups[:sample_size]
                )
        else:
            sampled_X_train = self.X_train_all
            sampled_y_train = self.y_train_all
            if (
                "sample_weight" in self.fit_kwargs
            ):  # NOTE: _prepare_sample_train_data is before kwargs is updated to fit_kwargs_by_estimator
                sampled_weight = self.sample_weight_all
            if self.groups is not None:
                groups = self.groups_all
        return sampled_X_train, sampled_y_train, sampled_weight, groups

    @staticmethod
    def _compute_with_config_base(
        config_w_resource: dict,
        state: "AutoMLState",
        estimator: str,
        is_report: bool = True,
    ) -> dict:
        if "FLAML_sample_size" in config_w_resource:
            sample_size = int(config_w_resource["FLAML_sample_size"])
        else:
            sample_size = state.data_size[0]

        this_estimator_kwargs = state.fit_kwargs_by_estimator.get(
            estimator
        ).copy()  # NOTE: _compute_with_config_base is after kwargs is updated to fit_kwargs_by_estimator
        (
            sampled_X_train,
            sampled_y_train,
            sampled_weight,
            groups,
        ) = state.task.prepare_sample_train_data(state, sample_size)
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
            if state.time_budget < 0
            else state.time_budget - state.time_from_start
            if sample_size == state.data_size[0]
            else (state.time_budget - state.time_from_start) / 2 * sample_size / state.data_size[0]
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
            state.train_time_limit if budget is None else min(budget, state.train_time_limit or np.inf),
            state.kf,
            config,
            state.task,
            estimator,
            state.eval_method,
            state.metric,
            state.best_loss,
            state.n_jobs,
            state.learner_classes.get(estimator),
            state.cv_score_agg_func,
            state.log_training_metric,
            this_estimator_kwargs,
            state.free_mem_ratio,
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
        if is_report is True:
            tune.report(**result)
        return result

    @classmethod
    def sanitize(cls, config: dict) -> dict:
        """Make a config ready for passing to estimator."""
        config = config.get("ml", config).copy()
        config.pop("FLAML_sample_size", None)
        config.pop("learner", None)
        config.pop("_choice_", None)
        return config

    def _train_with_config(
        self,
        estimator: str,
        config_w_resource: dict,
        sample_size: Optional[int] = None,
    ):
        if not sample_size:
            sample_size = config_w_resource.get("FLAML_sample_size", len(self.y_train_all))
        config = AutoMLState.sanitize(config_w_resource)

        this_estimator_kwargs = self.fit_kwargs_by_estimator.get(
            estimator
        ).copy()  # NOTE: _train_with_config is after kwargs is updated to fit_kwargs_by_estimator
        (
            sampled_X_train,
            sampled_y_train,
            sampled_weight,
            groups,
        ) = self.task.prepare_sample_train_data(self, sample_size)
        if sampled_weight is not None:
            weight = this_estimator_kwargs[
                "sample_weight"
            ]  # NOTE: _train_with_config is after kwargs is updated to fit_kwargs_by_estimator
            this_estimator_kwargs[
                "sample_weight"
            ] = sampled_weight  # NOTE: _train_with_config is after kwargs is updated to fit_kwargs_by_estimator
        if groups is not None:
            this_estimator_kwargs[
                "groups"
            ] = groups  # NOTE: _train_with_config is after kwargs is updated to fit_kwargs_by_estimator

        budget = None if self.time_budget < 0 else self.time_budget - self.time_from_start

        estimator, train_time = train_estimator(
            X_train=sampled_X_train,
            y_train=sampled_y_train,
            config_dic=config,
            task=self.task,
            estimator_name=estimator,
            n_jobs=self.n_jobs,
            estimator_class=self.learner_classes.get(estimator),
            budget=budget,
            fit_kwargs=this_estimator_kwargs,  # NOTE: _train_with_config is after kwargs is updated to fit_kwargs_by_estimator
            eval_metric=self.metric if hasattr(self, "metric") else "train_time",
            free_mem_ratio=self.free_mem_ratio,
        )

        if sampled_weight is not None:
            this_estimator_kwargs[
                "sample_weight"
            ] = weight  # NOTE: _train_with_config is after kwargs is updated to fit_kwargs_by_estimator

        return estimator, train_time
