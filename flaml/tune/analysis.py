'''
Copyright 2020 The Ray Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This source file is adapted here because ray does not fully support Windows.
'''
from typing import Dict, Optional
import numpy as np
from .trial import Trial

import logging
logger = logging.getLogger(__name__)


def is_nan_or_inf(value):
    return np.isnan(value) or np.isinf(value)


class ExperimentAnalysis:
    """Analyze results from a Tune experiment.
    """

    @property
    def best_trial(self) -> Trial:
        """Get the best trial of the experiment
        The best trial is determined by comparing the last trial results
        using the `metric` and `mode` parameters passed to `tune.run()`.
        If you didn't pass these parameters, use
        `get_best_trial(metric, mode, scope)` instead.
        """
        if not self.default_metric or not self.default_mode:
            raise ValueError(
                "To fetch the `best_trial`, pass a `metric` and `mode` "
                "parameter to `tune.run()`. Alternatively, use the "
                "`get_best_trial(metric, mode)` method to set the metric "
                "and mode explicitly.")
        return self.get_best_trial(self.default_metric, self.default_mode)

    @property
    def best_config(self) -> Dict:
        """Get the config of the best trial of the experiment
        The best trial is determined by comparing the last trial results
        using the `metric` and `mode` parameters passed to `tune.run()`.
        If you didn't pass these parameters, use
        `get_best_config(metric, mode, scope)` instead.
        """
        if not self.default_metric or not self.default_mode:
            raise ValueError(
                "To fetch the `best_config`, pass a `metric` and `mode` "
                "parameter to `tune.run()`. Alternatively, use the "
                "`get_best_config(metric, mode)` method to set the metric "
                "and mode explicitly.")
        return self.get_best_config(self.default_metric, self.default_mode)

    def _validate_metric(self, metric: str) -> str:
        if not metric and not self.default_metric:
            raise ValueError(
                "No `metric` has been passed and  `default_metric` has "
                "not been set. Please specify the `metric` parameter.")
        return metric or self.default_metric

    def _validate_mode(self, mode: str) -> str:
        if not mode and not self.default_mode:
            raise ValueError(
                "No `mode` has been passed and  `default_mode` has "
                "not been set. Please specify the `mode` parameter.")
        if mode and mode not in ["min", "max"]:
            raise ValueError("If set, `mode` has to be one of [min, max]")
        return mode or self.default_mode

    def get_best_trial(self,
                       metric: Optional[str] = None,
                       mode: Optional[str] = None,
                       scope: str = "last",
                       filter_nan_and_inf: bool = True) -> Optional[Trial]:
        """Retrieve the best trial object.
        Compares all trials' scores on ``metric``.
        If ``metric`` is not specified, ``self.default_metric`` will be used.
        If `mode` is not specified, ``self.default_mode`` will be used.
        These values are usually initialized by passing the ``metric`` and
        ``mode`` parameters to ``tune.run()``.
        Args:
            metric (str): Key for trial info to order on. Defaults to
                ``self.default_metric``.
            mode (str): One of [min, max]. Defaults to ``self.default_mode``.
            scope (str): One of [all, last, avg, last-5-avg, last-10-avg].
                If `scope=last`, only look at each trial's final step for
                `metric`, and compare across trials based on `mode=[min,max]`.
                If `scope=avg`, consider the simple average over all steps
                for `metric` and compare across trials based on
                `mode=[min,max]`. If `scope=last-5-avg` or `scope=last-10-avg`,
                consider the simple average over the last 5 or 10 steps for
                `metric` and compare across trials based on `mode=[min,max]`.
                If `scope=all`, find each trial's min/max score for `metric`
                based on `mode`, and compare trials based on `mode=[min,max]`.
            filter_nan_and_inf (bool): If True (default), NaN or infinite
                values are disregarded and these trials are never selected as
                the best trial.
        """
        metric = self._validate_metric(metric)
        mode = self._validate_mode(mode)

        if scope not in ["all", "last", "avg", "last-5-avg", "last-10-avg"]:
            raise ValueError(
                "ExperimentAnalysis: attempting to get best trial for "
                "metric {} for scope {} not in [\"all\", \"last\", \"avg\", "
                "\"last-5-avg\", \"last-10-avg\"]. "
                "If you didn't pass a `metric` parameter to `tune.run()`, "
                "you have to pass one when fetching the best trial.".format(
                    metric, scope))
        best_trial = None
        best_metric_score = None
        for trial in self.trials:
            if metric not in trial.metric_analysis:
                continue

            if scope in ["last", "avg", "last-5-avg", "last-10-avg"]:
                metric_score = trial.metric_analysis[metric][scope]
            else:
                metric_score = trial.metric_analysis[metric][mode]

            if filter_nan_and_inf and is_nan_or_inf(metric_score):
                continue

            if best_metric_score is None:
                best_metric_score = metric_score
                best_trial = trial
                continue

            if (mode == "max") and (best_metric_score < metric_score):
                best_metric_score = metric_score
                best_trial = trial
            elif (mode == "min") and (best_metric_score > metric_score):
                best_metric_score = metric_score
                best_trial = trial

        if not best_trial:
            logger.warning(
                "Could not find best trial. Did you pass the correct `metric` "
                "parameter?")
        return best_trial

    def get_best_config(self,
                        metric: Optional[str] = None,
                        mode: Optional[str] = None,
                        scope: str = "last") -> Optional[Dict]:
        """Retrieve the best config corresponding to the trial.
        Compares all trials' scores on `metric`.
        If ``metric`` is not specified, ``self.default_metric`` will be used.
        If `mode` is not specified, ``self.default_mode`` will be used.
        These values are usually initialized by passing the ``metric`` and
        ``mode`` parameters to ``tune.run()``.
        Args:
            metric (str): Key for trial info to order on. Defaults to
                ``self.default_metric``.
            mode (str): One of [min, max]. Defaults to ``self.default_mode``.
            scope (str): One of [all, last, avg, last-5-avg, last-10-avg].
                If `scope=last`, only look at each trial's final step for
                `metric`, and compare across trials based on `mode=[min,max]`.
                If `scope=avg`, consider the simple average over all steps
                for `metric` and compare across trials based on
                `mode=[min,max]`. If `scope=last-5-avg` or `scope=last-10-avg`,
                consider the simple average over the last 5 or 10 steps for
                `metric` and compare across trials based on `mode=[min,max]`.
                If `scope=all`, find each trial's min/max score for `metric`
                based on `mode`, and compare trials based on `mode=[min,max]`.
        """
        best_trial = self.get_best_trial(metric, mode, scope)
        return best_trial.config if best_trial else None
