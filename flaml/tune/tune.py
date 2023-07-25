# !
#  * Copyright (c) FLAML authors. All rights reserved.
#  * Licensed under the MIT License. See LICENSE file in the
#  * project root for license information.
from typing import Optional, Union, List, Callable, Tuple, Dict
import numpy as np
import datetime
import time
import os
import sys
from collections import defaultdict

try:
    from ray import __version__ as ray_version

    assert ray_version >= "1.10.0"
    from ray.tune.analysis import ExperimentAnalysis as EA
except (ImportError, AssertionError):
    ray_available = False
    from .analysis import ExperimentAnalysis as EA
else:
    ray_available = True

from .trial import Trial
from .result import DEFAULT_METRIC
import logging
from flaml.tune.spark.utils import PySparkOvertimeMonitor, check_spark

logger = logging.getLogger(__name__)
logger.propagate = False
_use_ray = True
_runner = None
_verbose = 0
_running_trial = None
_training_iteration = 0

INCUMBENT_RESULT = "__incumbent_result__"


class ExperimentAnalysis(EA):
    """Class for storing the experiment results."""

    def __init__(self, trials, metric, mode, lexico_objectives=None):
        try:
            super().__init__(self, None, trials, metric, mode)
            self.lexico_objectives = lexico_objectives
        except (TypeError, ValueError):
            self.trials = trials
            self.default_metric = metric or DEFAULT_METRIC
            self.default_mode = mode
            self.lexico_objectives = lexico_objectives

    @property
    def best_trial(self) -> Trial:
        if self.lexico_objectives is None:
            return super().best_trial
        else:
            return self.get_best_trial(self.default_metric, self.default_mode)

    @property
    def best_config(self) -> Dict:
        if self.lexico_objectives is None:
            return super().best_config
        else:
            return self.get_best_config(self.default_metric, self.default_mode)

    def lexico_best(self, trials):
        results = {index: trial.last_result for index, trial in enumerate(trials) if trial.last_result}
        metrics = self.lexico_objectives["metrics"]
        modes = self.lexico_objectives["modes"]
        f_best = {}
        keys = list(results.keys())
        length = len(keys)
        histories = defaultdict(list)
        for time_index in range(length):
            for objective, mode in zip(metrics, modes):
                histories[objective].append(
                    results[keys[time_index]][objective] if mode == "min" else -results[keys[time_index]][objective]
                )
        obj_initial = self.lexico_objectives["metrics"][0]
        feasible_index = np.array([*range(len(histories[obj_initial]))])
        for k_metric, k_mode in zip(self.lexico_objectives["metrics"], self.lexico_objectives["modes"]):
            k_values = np.array(histories[k_metric])
            k_target = (
                -self.lexico_objectives["targets"][k_metric]
                if k_mode == "max"
                else self.lexico_objectives["targets"][k_metric]
            )
            feasible_value = k_values.take(feasible_index)
            f_best[k_metric] = np.min(feasible_value)

            feasible_index_filter = np.where(
                feasible_value
                <= max(
                    f_best[k_metric] + self.lexico_objectives["tolerances"][k_metric]
                    if not isinstance(self.lexico_objectives["tolerances"][k_metric], str)
                    else f_best[k_metric]
                    * (1 + 0.01 * float(self.lexico_objectives["tolerances"][k_metric].replace("%", ""))),
                    k_target,
                )
            )[0]
            feasible_index = feasible_index.take(feasible_index_filter)
        best_trial = trials[feasible_index[-1]]
        return best_trial

    def get_best_trial(
        self,
        metric: Optional[str] = None,
        mode: Optional[str] = None,
        scope: str = "last",
        filter_nan_and_inf: bool = True,
    ) -> Optional[Trial]:
        if self.lexico_objectives is not None:
            best_trial = self.lexico_best(self.trials)
        else:
            best_trial = super().get_best_trial(metric, mode, scope, filter_nan_and_inf)
        return best_trial

    @property
    def best_result(self) -> Dict:
        if self.lexico_best is None:
            return super().best_result
        else:
            return self.best_trial.last_result


def report(_metric=None, **kwargs):
    """A function called by the HPO application to report final or intermediate
    results.

    Example:

    ```python
    import time
    from flaml import tune

    def compute_with_config(config):
        current_time = time.time()
        metric2minimize = (round(config['x'])-95000)**2
        time2eval = time.time() - current_time
        tune.report(metric2minimize=metric2minimize, time2eval=time2eval)

    analysis = tune.run(
        compute_with_config,
        config={
            'x': tune.lograndint(lower=1, upper=1000000),
            'y': tune.randint(lower=1, upper=1000000)
        },
        metric='metric2minimize', mode='min',
        num_samples=1000000, time_budget_s=60, use_ray=False)

    print(analysis.trials[-1].last_result)
    ```

    Args:
        _metric: Optional default anonymous metric for ``tune.report(value)``.
            (For compatibility with ray.tune.report)
        **kwargs: Any key value pair to be reported.

    Raises:
        StopIteration (when not using ray, i.e., _use_ray=False):
            A StopIteration exception is raised if the trial has been signaled to stop.
        SystemExit (when using ray):
            A SystemExit exception is raised if the trial has been signaled to stop by ray.
    """
    global _use_ray
    global _verbose
    global _running_trial
    global _training_iteration
    if _use_ray:
        try:
            from ray import tune

            return tune.report(_metric, **kwargs)
        except ImportError:
            # calling tune.report() outside tune.run()
            return
    result = kwargs
    if _metric:
        result[DEFAULT_METRIC] = _metric
    trial = getattr(_runner, "running_trial", None)
    if not trial:
        return None
    if _running_trial == trial:
        _training_iteration += 1
    else:
        _training_iteration = 0
        _running_trial = trial
    result["training_iteration"] = _training_iteration
    result["config"] = trial.config
    if INCUMBENT_RESULT in result["config"]:
        del result["config"][INCUMBENT_RESULT]
    for key, value in trial.config.items():
        result["config/" + key] = value
    _runner.process_trial_result(trial, result)
    if _verbose > 2:
        logger.info(f"result: {result}")
    if trial.is_finished():
        raise StopIteration


def run(
    evaluation_function,
    config: Optional[dict] = None,
    low_cost_partial_config: Optional[dict] = None,
    cat_hp_cost: Optional[dict] = None,
    metric: Optional[str] = None,
    mode: Optional[str] = None,
    time_budget_s: Union[int, float] = None,
    points_to_evaluate: Optional[List[dict]] = None,
    evaluated_rewards: Optional[List] = None,
    resource_attr: Optional[str] = None,
    min_resource: Optional[float] = None,
    max_resource: Optional[float] = None,
    reduction_factor: Optional[float] = None,
    scheduler=None,
    search_alg=None,
    verbose: Optional[int] = 2,
    local_dir: Optional[str] = None,
    num_samples: Optional[int] = 1,
    resources_per_trial: Optional[dict] = None,
    config_constraints: Optional[List[Tuple[Callable[[dict], float], str, float]]] = None,
    metric_constraints: Optional[List[Tuple[str, str, float]]] = None,
    max_failure: Optional[int] = 100,
    use_ray: Optional[bool] = False,
    use_spark: Optional[bool] = False,
    use_incumbent_result_in_evaluation: Optional[bool] = None,
    log_file_name: Optional[str] = None,
    lexico_objectives: Optional[dict] = None,
    force_cancel: Optional[bool] = False,
    n_concurrent_trials: Optional[int] = 0,
    **ray_args,
):
    """The function-based way of performing HPO.

    Example:

    ```python
    import time
    from flaml import tune

    def compute_with_config(config):
        current_time = time.time()
        metric2minimize = (round(config['x'])-95000)**2
        time2eval = time.time() - current_time
        tune.report(metric2minimize=metric2minimize, time2eval=time2eval)
        # if the evaluation fails unexpectedly and the exception is caught,
        # and it doesn't inform the goodness of the config,
        # return {}
        # if the failure indicates a config is bad,
        # report a bad metric value like np.inf or -np.inf
        # depending on metric mode being min or max

    analysis = tune.run(
        compute_with_config,
        config={
            'x': tune.lograndint(lower=1, upper=1000000),
            'y': tune.randint(lower=1, upper=1000000)
        },
        metric='metric2minimize', mode='min',
        num_samples=-1, time_budget_s=60, use_ray=False)

    print(analysis.trials[-1].last_result)
    ```

    Args:
        evaluation_function: A user-defined evaluation function.
            It takes a configuration as input, outputs a evaluation
            result (can be a numerical value or a dictionary of string
            and numerical value pairs) for the input configuration.
            For machine learning tasks, it usually involves training and
            scoring a machine learning model, e.g., through validation loss.
        config: A dictionary to specify the search space.
        low_cost_partial_config: A dictionary from a subset of
            controlled dimensions to the initial low-cost values.
            e.g., ```{'n_estimators': 4, 'max_leaves': 4}```

        cat_hp_cost: A dictionary from a subset of categorical dimensions
            to the relative cost of each choice.
            e.g., ```{'tree_method': [1, 1, 2]}```
            i.e., the relative cost of the
            three choices of 'tree_method' is 1, 1 and 2 respectively
        metric: A string of the metric name to optimize for.
        mode: A string in ['min', 'max'] to specify the objective as
            minimization or maximization.
        time_budget_s: int or float | The time budget in seconds.
        points_to_evaluate: A list of initial hyperparameter
            configurations to run first.
        evaluated_rewards (list): If you have previously evaluated the
            parameters passed in as points_to_evaluate you can avoid
            re-running those trials by passing in the reward attributes
            as a list so the optimiser can be told the results without
            needing to re-compute the trial. Must be the same or shorter length than
            points_to_evaluate.
            e.g.,

    ```python
    points_to_evaluate = [
        {"b": .99, "cost_related": {"a": 3}},
        {"b": .99, "cost_related": {"a": 2}},
    ]
    evaluated_rewards = [3.0]
    ```

            means that you know the reward for the first config in
            points_to_evaluate is 3.0 and want to inform run().

        resource_attr: A string to specify the resource dimension used by
            the scheduler via "scheduler".
        min_resource: A float of the minimal resource to use for the resource_attr.
        max_resource: A float of the maximal resource to use for the resource_attr.
        reduction_factor: A float of the reduction factor used for incremental
            pruning.
        scheduler: A scheduler for executing the experiment. Can be None, 'flaml',
            'asha' (or  'async_hyperband', 'asynchyperband') or a custom instance of the TrialScheduler class. Default is None:
            in this case when resource_attr is provided, the 'flaml' scheduler will be
            used, otherwise no scheduler will be used. When set 'flaml', an
            authentic scheduler implemented in FLAML will be used. It does not
            require users to report intermediate results in evaluation_function.
            Find more details about this scheduler in this paper
            https://arxiv.org/pdf/1911.04706.pdf).
            When set 'asha', the input for arguments "resource_attr",
            "min_resource", "max_resource" and "reduction_factor" will be passed
            to ASHA's "time_attr",  "max_t", "grace_period" and "reduction_factor"
            respectively. You can also provide a self-defined scheduler instance
            of the TrialScheduler class. When 'asha' or self-defined scheduler is
            used, you usually need to report intermediate results in the evaluation
            function via 'tune.report()'.
            If you would like to do some cleanup opearation when the trial is stopped
            by the scheduler, you can catch the `StopIteration` (when not using ray)
            or `SystemExit` (when using ray) exception explicitly,
            as shown in the following example.
            Please find more examples using different types of schedulers
            and how to set up the corresponding evaluation functions in
            test/tune/test_scheduler.py, and test/tune/example_scheduler.py.
    ```python
    def easy_objective(config):
        width, height = config["width"], config["height"]
        for step in range(config["steps"]):
            intermediate_score = evaluation_fn(step, width, height)
            try:
                tune.report(iterations=step, mean_loss=intermediate_score)
            except (StopIteration, SystemExit):
                # do cleanup operation here
                return
    ```
        search_alg: An instance/string of the search algorithm
            to be used. The same instance can be used for iterative tuning.
            e.g.,

    ```python
    from flaml import BlendSearch
    algo = BlendSearch(metric='val_loss', mode='min',
            space=search_space,
            low_cost_partial_config=low_cost_partial_config)
    for i in range(10):
        analysis = tune.run(compute_with_config,
            search_alg=algo, use_ray=False)
        print(analysis.trials[-1].last_result)
    ```

        verbose: 0, 1, 2, or 3. If ray or spark backend is used, their verbosity will be
            affected by this argument. 0 = silent, 1 = only status updates,
            2 = status and brief trial results, 3 = status and detailed trial results.
            Defaults to 2.
        local_dir: A string of the local dir to save ray logs if ray backend is
            used; or a local dir to save the tuning log.
        num_samples: An integer of the number of configs to try. Defaults to 1.
        resources_per_trial: A dictionary of the hardware resources to allocate
            per trial, e.g., `{'cpu': 1}`. It is only valid when using ray backend
            (by setting 'use_ray = True'). It shall be used when you need to do
            [parallel tuning](/docs/Use-Cases/Tune-User-Defined-Function#parallel-tuning).
        config_constraints: A list of config constraints to be satisfied.
            e.g., ```config_constraints = [(mem_size, '<=', 1024**3)]```

            mem_size is a function which produces a float number for the bytes
            needed for a config.
            It is used to skip configs which do not fit in memory.
        metric_constraints: A list of metric constraints to be satisfied.
            e.g., `['precision', '>=', 0.9]`. The sign can be ">=" or "<=".
        max_failure: int | the maximal consecutive number of failures to sample
            a trial before the tuning is terminated.
        use_ray: A boolean of whether to use ray as the backend.
        use_spark: A boolean of whether to use spark as the backend.
        log_file_name: A string of the log file name. Default to None.
            When set to None:
                if local_dir is not given, no log file is created;
                if local_dir is given, the log file name will be autogenerated under local_dir.
            Only valid when verbose > 0 or use_ray is True.
        lexico_objectives: dict, default=None | It specifics information needed to perform multi-objective
            optimization with lexicographic preferences. When lexico_objectives is not None, the arguments metric,
            mode, will be invalid, and flaml's tune uses CFO
            as the `search_alg`, which makes the input (if provided) `search_alg' invalid.
            This dictionary shall contain the following fields of key-value pairs:
            - "metrics":  a list of optimization objectives with the orders reflecting the priorities/preferences of the
            objectives.
            - "modes" (optional): a list of optimization modes (each mode either "min" or "max") corresponding to the
            objectives in the metric list. If not provided, we use "min" as the default mode for all the objectives.
            - "targets" (optional): a dictionary to specify the optimization targets on the objectives. The keys are the
            metric names (provided in "metric"), and the values are the numerical target values.
            - "tolerances" (optional): a dictionary to specify the optimality tolerances on objectives. The keys are the metric names (provided in "metrics"), and the values are the absolute/percentage tolerance in the form of numeric/string.
            E.g.,
    ```python
    lexico_objectives = {
        "metrics": ["error_rate", "pred_time"],
        "modes": ["min", "min"],
        "tolerances": {"error_rate": 0.01, "pred_time": 0.0},
        "targets": {"error_rate": 0.0},
    }
    ```
            We also support percentage tolerance.
            E.g.,
    ```python
    lexico_objectives = {
        "metrics": ["error_rate", "pred_time"],
        "modes": ["min", "min"],
        "tolerances": {"error_rate": "5%", "pred_time": "0%"},
        "targets": {"error_rate": 0.0},
    }
    ```
        force_cancel: boolean, default=False | Whether to forcely cancel the PySpark job if overtime.
        n_concurrent_trials: int, default=0 | The number of concurrent trials when perform hyperparameter
            tuning with Spark. Only valid when use_spark=True and spark is required:
            `pip install flaml[spark]`. Please check
            [here](https://spark.apache.org/docs/latest/api/python/getting_started/install.html)
            for more details about installing Spark. When tune.run() is called from AutoML, it will be
            overwritten by the value of `n_concurrent_trials` in AutoML. When <= 0, the concurrent trials
            will be set to the number of executors.
        **ray_args: keyword arguments to pass to ray.tune.run().
            Only valid when use_ray=True.
    """
    global _use_ray
    global _verbose
    global _running_trial
    global _training_iteration
    old_use_ray = _use_ray
    old_verbose = _verbose
    old_running_trial = _running_trial
    old_training_iteration = _training_iteration
    if log_file_name:
        dir_name = os.path.dirname(log_file_name)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
    elif local_dir and verbose > 0:
        os.makedirs(local_dir, exist_ok=True)
        log_file_name = os.path.join(local_dir, "tune_" + str(datetime.datetime.now()).replace(":", "-") + ".log")
    if use_ray and use_spark:
        raise ValueError("use_ray and use_spark cannot be both True.")
    if not use_ray:
        _use_ray = False
        _verbose = verbose
        old_handlers = logger.handlers
        old_level = logger.getEffectiveLevel()
        logger.handlers = []
        global _runner
        old_runner = _runner
        assert not ray_args, "ray_args is only valid when use_ray=True"
        if (
            old_handlers
            and isinstance(old_handlers[0], logging.StreamHandler)
            and not isinstance(old_handlers[0], logging.FileHandler)
        ):
            # Add the console handler.
            logger.addHandler(old_handlers[0])
        if verbose > 0:
            if log_file_name:
                logger.addHandler(logging.FileHandler(log_file_name))
            elif not logger.hasHandlers():
                # Add the console handler.
                _ch = logging.StreamHandler(stream=sys.stdout)
                logger_formatter = logging.Formatter(
                    "[%(name)s: %(asctime)s] {%(lineno)d} %(levelname)s - %(message)s",
                    "%m-%d %H:%M:%S",
                )
                _ch.setFormatter(logger_formatter)
                logger.addHandler(_ch)
            if verbose <= 2:
                logger.setLevel(logging.INFO)
            else:
                logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.CRITICAL)

    from .searcher.blendsearch import BlendSearch, CFO, RandomSearch

    if lexico_objectives is not None:
        if "modes" not in lexico_objectives.keys():
            lexico_objectives["modes"] = ["min"] * len(lexico_objectives["metrics"])
        for t_metric, t_mode in zip(lexico_objectives["metrics"], lexico_objectives["modes"]):
            if t_metric not in lexico_objectives["tolerances"].keys():
                lexico_objectives["tolerances"][t_metric] = 0
            if t_metric not in lexico_objectives["targets"].keys():
                lexico_objectives["targets"][t_metric] = -float("inf") if t_mode == "min" else float("inf")
    if search_alg is None or isinstance(search_alg, str):
        if isinstance(search_alg, str):
            assert search_alg in [
                "BlendSearch",
                "CFO",
                "CFOCat",
                "RandomSearch",
            ], f"search_alg={search_alg} is not recognized. 'BlendSearch', 'CFO', 'CFOcat' and 'RandomSearch' are supported."

        flaml_scheduler_resource_attr = (
            flaml_scheduler_min_resource
        ) = flaml_scheduler_max_resource = flaml_scheduler_reduction_factor = None
        if scheduler in (None, "flaml"):
            # when scheduler is set 'flaml' or None, we will use a scheduler that is
            # authentic to the search algorithms in flaml. After setting up
            # the search algorithm accordingly, we need to set scheduler to
            # None in case it is later used in the trial runner.
            flaml_scheduler_resource_attr = resource_attr
            flaml_scheduler_min_resource = min_resource
            flaml_scheduler_max_resource = max_resource
            flaml_scheduler_reduction_factor = reduction_factor
            scheduler = None
        if lexico_objectives:
            # TODO: Modify after supporting BlendSearch in lexicographic optimization
            SearchAlgorithm = CFO
            logger.info(
                f"Using search algorithm {SearchAlgorithm.__name__} for lexicographic optimization. Note that when providing other search algorithms, we use CFO instead temporarily."
            )
            metric = lexico_objectives["metrics"][0] or DEFAULT_METRIC
        else:
            if not search_alg or search_alg == "BlendSearch":
                try:
                    import optuna as _

                    SearchAlgorithm = BlendSearch
                    logger.info("Using search algorithm {}.".format(SearchAlgorithm.__name__))
                except ImportError:
                    if search_alg == "BlendSearch":
                        raise ValueError("To use BlendSearch, run: pip install flaml[blendsearch]")
                    else:
                        SearchAlgorithm = CFO
                        logger.warning("Using CFO for search. To use BlendSearch, run: pip install flaml[blendsearch]")
            else:
                SearchAlgorithm = locals()[search_alg]
                logger.info("Using search algorithm {}.".format(SearchAlgorithm.__name__))
            metric = metric or DEFAULT_METRIC
        search_alg = SearchAlgorithm(
            metric=metric,
            mode=mode,
            space=config,
            points_to_evaluate=points_to_evaluate,
            evaluated_rewards=evaluated_rewards,
            low_cost_partial_config=low_cost_partial_config,
            cat_hp_cost=cat_hp_cost,
            time_budget_s=time_budget_s,
            num_samples=num_samples,
            resource_attr=flaml_scheduler_resource_attr,
            min_resource=flaml_scheduler_min_resource,
            max_resource=flaml_scheduler_max_resource,
            reduction_factor=flaml_scheduler_reduction_factor,
            config_constraints=config_constraints,
            metric_constraints=metric_constraints,
            use_incumbent_result_in_evaluation=use_incumbent_result_in_evaluation,
            lexico_objectives=lexico_objectives,
        )
    else:
        if metric is None or mode is None:
            if lexico_objectives:
                metric = lexico_objectives["metrics"][0] or metric or search_alg.metric or DEFAULT_METRIC
                mode = lexico_objectives["modes"][0] or mode or search_alg.mode
            else:
                metric = metric or search_alg.metric or DEFAULT_METRIC
                mode = mode or search_alg.mode
        if ray_available and use_ray:
            if ray_version.startswith("1."):
                from ray.tune.suggest import ConcurrencyLimiter
            else:
                from ray.tune.search import ConcurrencyLimiter
        else:
            from flaml.tune.searcher.suggestion import ConcurrencyLimiter
        if (
            search_alg.__class__.__name__
            in [
                "BlendSearch",
                "CFO",
                "CFOCat",
            ]
            and use_incumbent_result_in_evaluation is not None
        ):
            search_alg.use_incumbent_result_in_evaluation = use_incumbent_result_in_evaluation
        searcher = search_alg.searcher if isinstance(search_alg, ConcurrencyLimiter) else search_alg
        if lexico_objectives:
            # TODO: Modify after supporting BlendSearch in lexicographic optimization
            assert search_alg.__class__.__name__ in [
                "CFO",
            ], "If lexico_objectives is not None, the search_alg must be CFO for now."
            search_alg.lexico_objective = lexico_objectives

        if isinstance(searcher, BlendSearch):
            setting = {}
            if time_budget_s:
                setting["time_budget_s"] = time_budget_s
            if num_samples > 0:
                setting["num_samples"] = num_samples
            searcher.set_search_properties(metric, mode, config, **setting)
        else:
            searcher.set_search_properties(metric, mode, config)
    if scheduler in ("asha", "asynchyperband", "async_hyperband"):
        params = {}
        # scheduler resource_dimension=resource_attr
        if resource_attr:
            params["time_attr"] = resource_attr
        if max_resource:
            params["max_t"] = max_resource
        if min_resource:
            params["grace_period"] = min_resource
        if reduction_factor:
            params["reduction_factor"] = reduction_factor
        if ray_available:
            from ray.tune.schedulers import ASHAScheduler

            scheduler = ASHAScheduler(**params)
    if use_ray:
        try:
            from ray import tune
        except ImportError:
            raise ImportError("Failed to import ray tune. " "Please install ray[tune] or set use_ray=False")
        _use_ray = True
        try:
            analysis = tune.run(
                evaluation_function,
                metric=metric,
                mode=mode,
                search_alg=search_alg,
                scheduler=scheduler,
                time_budget_s=time_budget_s,
                verbose=verbose,
                local_dir=local_dir,
                num_samples=num_samples,
                resources_per_trial=resources_per_trial,
                **ray_args,
            )
            if log_file_name:
                with open(log_file_name, "w") as f:
                    for trial in analysis.trials:
                        f.write(f"result: {trial.last_result}\n")
            return analysis
        finally:
            _use_ray = old_use_ray
            _verbose = old_verbose
            _running_trial = old_running_trial
            _training_iteration = old_training_iteration

    if use_spark:
        # parallel run with spark
        spark_available, spark_error_msg = check_spark()
        if not spark_available:
            raise spark_error_msg
        try:
            from pyspark.sql import SparkSession
            from joblib import Parallel, delayed, parallel_backend
            from joblibspark import register_spark
        except ImportError as e:
            raise ImportError(f"{e}. Try pip install flaml[spark] or set use_spark=False.")
        from flaml.tune.searcher.suggestion import ConcurrencyLimiter
        from .trial_runner import SparkTrialRunner

        register_spark()
        spark = SparkSession.builder.getOrCreate()
        sc = spark._jsc.sc()
        num_executors = len([executor.host() for executor in sc.statusTracker().getExecutorInfos()]) - 1
        """
        By default, the number of executors is the number of VMs in the cluster. And we can
        launch one trial per executor. However, sometimes we can launch more trials than
        the number of executors (e.g., local mode). In this case, we can set the environment
        variable `FLAML_MAX_CONCURRENT` to override the detected `num_executors`.

        `max_concurrent` is the maximum number of concurrent trials defined by `search_alg`,
        `FLAML_MAX_CONCURRENT` will also be used to override `max_concurrent` if `search_alg`
        is not an instance of `ConcurrencyLimiter`.

        The final number of concurrent trials is the minimum of `max_concurrent` and
        `num_executors` if `n_concurrent_trials<=0` (default, automl cases), otherwise the
        minimum of `max_concurrent` and `n_concurrent_trials` (tuning cases).
        """
        time_start = time.time()
        try:
            FLAML_MAX_CONCURRENT = int(os.getenv("FLAML_MAX_CONCURRENT", 0))
        except ValueError:
            FLAML_MAX_CONCURRENT = 0
        num_executors = max(num_executors, FLAML_MAX_CONCURRENT, 1)
        max_spark_parallelism = max(spark.sparkContext.defaultParallelism, FLAML_MAX_CONCURRENT)
        if scheduler:
            scheduler.set_search_properties(metric=metric, mode=mode)
        if isinstance(search_alg, ConcurrencyLimiter):
            max_concurrent = max(1, search_alg.max_concurrent)
        else:
            max_concurrent = max(1, max_spark_parallelism)
        n_concurrent_trials = min(
            n_concurrent_trials if n_concurrent_trials > 0 else num_executors,
            max_concurrent,
        )
        with parallel_backend("spark"):
            with Parallel(n_jobs=n_concurrent_trials, verbose=max(0, (verbose - 1) * 50)) as parallel:
                try:
                    _runner = SparkTrialRunner(
                        search_alg=search_alg,
                        scheduler=scheduler,
                        metric=metric,
                        mode=mode,
                    )
                    num_trials = 0
                    if time_budget_s is None:
                        time_budget_s = np.inf
                    num_failures = 0
                    upperbound_num_failures = (len(evaluated_rewards) if evaluated_rewards else 0) + max_failure
                    while (
                        time.time() - time_start < time_budget_s
                        and (num_samples < 0 or num_trials < num_samples)
                        and num_failures < upperbound_num_failures
                    ):
                        while len(_runner.running_trials) < n_concurrent_trials:
                            # suggest trials for spark
                            trial_next = _runner.step()
                            if trial_next:
                                num_trials += 1
                            else:
                                num_failures += 1  # break with upperbound_num_failures consecutive failures
                                logger.debug(f"consecutive failures is {num_failures}")
                                if num_failures >= upperbound_num_failures:
                                    break
                        trials_to_run = _runner.running_trials
                        if not trials_to_run:
                            logger.warning(f"fail to sample a trial for {max_failure} times in a row, stopping.")
                            break
                        logger.info(
                            f"Number of trials: {num_trials}/{num_samples}, {len(_runner.running_trials)} RUNNING,"
                            f" {len(_runner._trials) - len(_runner.running_trials)} TERMINATED"
                        )
                        logger.debug(
                            f"Configs of Trials to run: {[trial_to_run.config for trial_to_run in trials_to_run]}"
                        )
                        results = None
                        with PySparkOvertimeMonitor(time_start, time_budget_s, force_cancel, parallel=parallel):
                            results = parallel(
                                delayed(evaluation_function)(trial_to_run.config) for trial_to_run in trials_to_run
                            )
                        # results = [evaluation_function(trial_to_run.config) for trial_to_run in trials_to_run]
                        while results:
                            result = results.pop(0)
                            trial_to_run = trials_to_run[0]
                            _runner.running_trial = trial_to_run
                            if result is not None:
                                if isinstance(result, dict):
                                    if result:
                                        logger.info(f"Brief result: {result}")
                                        report(**result)
                                    else:
                                        # When the result returned is an empty dict, set the trial status to error
                                        trial_to_run.set_status(Trial.ERROR)
                                else:
                                    logger.info("Brief result: {}".format({metric: result}))
                                    report(_metric=result)
                            _runner.stop_trial(trial_to_run)
                        num_failures = 0
                    analysis = ExperimentAnalysis(
                        _runner.get_trials(),
                        metric=metric,
                        mode=mode,
                        lexico_objectives=lexico_objectives,
                    )
                    return analysis
                finally:
                    # recover the global variables in case of nested run
                    _use_ray = old_use_ray
                    _verbose = old_verbose
                    _running_trial = old_running_trial
                    _training_iteration = old_training_iteration
                    if not use_ray:
                        _runner = old_runner
                        logger.handlers = old_handlers
                        logger.setLevel(old_level)

    # simple sequential run without using tune.run() from ray
    time_start = time.time()
    _use_ray = False
    if scheduler:
        scheduler.set_search_properties(metric=metric, mode=mode)
    from .trial_runner import SequentialTrialRunner

    try:
        _runner = SequentialTrialRunner(
            search_alg=search_alg,
            scheduler=scheduler,
            metric=metric,
            mode=mode,
        )
        num_trials = 0
        if time_budget_s is None:
            time_budget_s = np.inf
        num_failures = 0
        upperbound_num_failures = (len(evaluated_rewards) if evaluated_rewards else 0) + max_failure
        while (
            time.time() - time_start < time_budget_s
            and (num_samples < 0 or num_trials < num_samples)
            and num_failures < upperbound_num_failures
        ):
            trial_to_run = _runner.step()
            if trial_to_run:
                num_trials += 1
                if verbose:
                    logger.info(f"trial {num_trials} config: {trial_to_run.config}")
                result = None
                with PySparkOvertimeMonitor(time_start, time_budget_s, force_cancel):
                    result = evaluation_function(trial_to_run.config)
                if result is not None:
                    if isinstance(result, dict):
                        if result:
                            report(**result)
                        else:
                            # When the result returned is an empty dict, set the trial status to error
                            trial_to_run.set_status(Trial.ERROR)
                    else:
                        report(_metric=result)
                _runner.stop_trial(trial_to_run)
                num_failures = 0
                if trial_to_run.last_result is None:
                    # application stops tuning by returning None
                    # TODO document this feature when it is finalized
                    break
            else:
                # break with upperbound_num_failures consecutive failures
                num_failures += 1
        if num_failures == upperbound_num_failures:
            logger.warning(f"fail to sample a trial for {max_failure} times in a row, stopping.")
        analysis = ExperimentAnalysis(
            _runner.get_trials(),
            metric=metric,
            mode=mode,
            lexico_objectives=lexico_objectives,
        )
        return analysis
    finally:
        # recover the global variables in case of nested run
        _use_ray = old_use_ray
        _verbose = old_verbose
        _running_trial = old_running_trial
        _training_iteration = old_training_iteration
        if not use_ray:
            _runner = old_runner
            logger.handlers = old_handlers
            logger.setLevel(old_level)


class Tuner:
    """Tuner is the class-based way of launching hyperparameter tuning jobs compatible with Ray Tune 2.

    Args:
        trainable: A user-defined evaluation function.
            It takes a configuration as input, outputs a evaluation
            result (can be a numerical value or a dictionary of string
            and numerical value pairs) for the input configuration.
            For machine learning tasks, it usually involves training and
            scoring a machine learning model, e.g., through validation loss.
        param_space: Search space of the tuning job.
            One thing to note is that both preprocessor and dataset can be tuned here.
        tune_config: Tuning algorithm specific configs.
            Refer to ray.tune.tune_config.TuneConfig for more info.
        run_config: Runtime configuration that is specific to individual trials.
            If passed, this will overwrite the run config passed to the Trainer,
            if applicable. Refer to ray.air.config.RunConfig for more info.

    Usage pattern:

    .. code-block:: python

        from sklearn.datasets import load_breast_cancer

        from ray import tune
        from ray.data import from_pandas
        from ray.air.config import RunConfig, ScalingConfig
        from ray.train.xgboost import XGBoostTrainer
        from ray.tune.tuner import Tuner

        def get_dataset():
            data_raw = load_breast_cancer(as_frame=True)
            dataset_df = data_raw["data"]
            dataset_df["target"] = data_raw["target"]
            dataset = from_pandas(dataset_df)
            return dataset

        trainer = XGBoostTrainer(
            label_column="target",
            params={},
            datasets={"train": get_dataset()},
        )

        param_space = {
            "scaling_config": ScalingConfig(
                num_workers=tune.grid_search([2, 4]),
                resources_per_worker={
                    "CPU": tune.grid_search([1, 2]),
                },
            ),
            # You can even grid search various datasets in Tune.
            # "datasets": {
            #     "train": tune.grid_search(
            #         [ds1, ds2]
            #     ),
            # },
            "params": {
                "objective": "binary:logistic",
                "tree_method": "approx",
                "eval_metric": ["logloss", "error"],
                "eta": tune.loguniform(1e-4, 1e-1),
                "subsample": tune.uniform(0.5, 1.0),
                "max_depth": tune.randint(1, 9),
            },
        }
        tuner = Tuner(trainable=trainer, param_space=param_space,
            run_config=RunConfig(name="my_tune_run"))
        analysis = tuner.fit()

    To retry a failed tune run, you can then do

    .. code-block:: python

        tuner = Tuner.restore(experiment_checkpoint_dir)
        tuner.fit()

    ``experiment_checkpoint_dir`` can be easily located near the end of the
    console output of your first failed run.
    """
