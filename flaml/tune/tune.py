# !
#  * Copyright (c) Microsoft Corporation. All rights reserved.
#  * Licensed under the MIT License. See LICENSE file in the
#  * project root for license information.
from typing import Optional, Union, List, Callable, Tuple
import numpy as np
import datetime
import time

try:
    from ray import __version__ as ray_version

    assert ray_version >= "1.0.0"
    from ray.tune.analysis import ExperimentAnalysis as EA

    ray_import = True
except (ImportError, AssertionError):
    ray_import = False
    from .analysis import ExperimentAnalysis as EA

from .result import DEFAULT_METRIC
import logging

logger = logging.getLogger(__name__)


_use_ray = True
_runner = None
_verbose = 0
_running_trial = None
_training_iteration = 0

INCUMBENT_RESULT = "__incumbent_result__"


class ExperimentAnalysis(EA):
    """Class for storing the experiment results."""

    def __init__(self, trials, metric, mode):
        try:
            super().__init__(self, None, trials, metric, mode)
        except (TypeError, ValueError):
            self.trials = trials
            self.default_metric = metric or DEFAULT_METRIC
            self.default_mode = mode


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
    """
    global _use_ray
    global _verbose
    global _running_trial
    global _training_iteration
    if _use_ray:
        from ray import tune

        return tune.report(_metric, **kwargs)
    else:
        result = kwargs
        if _metric:
            result[DEFAULT_METRIC] = _metric
        trial = _runner.running_trial
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
        _runner.process_trial_result(_runner.running_trial, result)
        result["time_total_s"] = trial.last_update_time - trial.start_time
        if _verbose > 2:
            logger.info(f"result: {result}")
        if _runner.running_trial.is_finished():
            return None
        else:
            return True


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
    config_constraints: Optional[
        List[Tuple[Callable[[dict], float], str, float]]
    ] = None,
    metric_constraints: Optional[List[Tuple[str, str, float]]] = None,
    max_failure: Optional[int] = 100,
    use_ray: Optional[bool] = False,
    use_incumbent_result_in_evaluation: Optional[bool] = None,
):
    """The trigger for HPO.

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
            needing to re-compute the trial. Must be the same length as
            points_to_evaluate.
            e.g.,

    ```python
    points_to_evaluate = [
        {"b": .99, "cost_related": {"a": 3}},
        {"b": .99, "cost_related": {"a": 2}},
    ]
    evaluated_rewards=[3.0, 1.0]
    ```

            means that you know the reward for the two configs in
            points_to_evaluate are 3.0 and 1.0 respectively and want to
            inform run().

        resource_attr: A string to specify the resource dimension used by
            the scheduler via "scheduler".
        min_resource: A float of the minimal resource to use for the resource_attr.
        max_resource: A float of the maximal resource to use for the resource_attr.
        reduction_factor: A float of the reduction factor used for incremental
            pruning.
        scheduler: A scheduler for executing the experiment. Can be None, 'flaml',
            'asha' or a custom instance of the TrialScheduler class. Default is None:
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
            function. Please find examples using different types of schedulers
            and how to set up the corresponding evaluation functions in
            test/tune/test_scheduler.py. TODO: point to notebook examples.
        search_alg: An instance of BlendSearch as the search algorithm
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

        verbose: 0, 1, 2, or 3. Verbosity mode for ray if ray backend is used.
            0 = silent, 1 = only status updates, 2 = status and brief trial
            results, 3 = status and detailed trial results. Defaults to 2.
        local_dir: A string of the local dir to save ray logs if ray backend is
            used; or a local dir to save the tuning log.
        num_samples: An integer of the number of configs to try. Defaults to 1.
        resources_per_trial: A dictionary of the hardware resources to allocate
            per trial, e.g., `{'cpu': 1}`. Only valid when using ray backend.
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
    """
    global _use_ray
    global _verbose
    if not use_ray:
        _verbose = verbose
        if verbose > 0:
            import os

            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
                logger.addHandler(
                    logging.FileHandler(
                        local_dir
                        + "/tune_"
                        + str(datetime.datetime.now()).replace(":", "-")
                        + ".log"
                    )
                )
            elif not logger.handlers:
                # Add the console handler.
                _ch = logging.StreamHandler()
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

    from ..searcher.blendsearch import BlendSearch, CFO

    if search_alg is None:
        flaml_scheduler_resource_attr = (
            flaml_scheduler_min_resource
        ) = flaml_scheduler_max_resource = flaml_scheduler_reduction_factor = None
        if scheduler in (None, "flaml"):

            # when scheduler is set 'flaml', we will use a scheduler that is
            # authentic to the search algorithms in flaml. After setting up
            # the search algorithm accordingly, we need to set scheduler to
            # None in case it is later used in the trial runner.
            flaml_scheduler_resource_attr = resource_attr
            flaml_scheduler_min_resource = min_resource
            flaml_scheduler_max_resource = max_resource
            flaml_scheduler_reduction_factor = reduction_factor
            scheduler = None
        try:
            import optuna

            SearchAlgorithm = BlendSearch
        except ImportError:
            SearchAlgorithm = CFO
            logger.warning(
                "Using CFO for search. To use BlendSearch, run: pip install flaml[blendsearch]"
            )

        search_alg = SearchAlgorithm(
            metric=metric or DEFAULT_METRIC,
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
        )
    else:
        if metric is None or mode is None:
            metric = metric or search_alg.metric
            mode = mode or search_alg.mode
        if ray_import:
            from ray.tune.suggest import ConcurrencyLimiter
        else:
            from flaml.searcher.suggestion import ConcurrencyLimiter
        if (
            search_alg.__class__.__name__
            in [
                "BlendSearch",
                "CFO",
                "CFOCat",
            ]
            and use_incumbent_result_in_evaluation is not None
        ):
            search_alg.use_incumbent_result_in_evaluation = (
                use_incumbent_result_in_evaluation
            )
        searcher = (
            search_alg.searcher
            if isinstance(search_alg, ConcurrencyLimiter)
            else search_alg
        )
        if isinstance(searcher, BlendSearch):
            setting = {}
            if time_budget_s:
                setting["time_budget_s"] = time_budget_s
            if num_samples > 0:
                setting["num_samples"] = num_samples
            searcher.set_search_properties(metric, mode, config, setting)
        else:
            searcher.set_search_properties(metric, mode, config)
    if scheduler == "asha":
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
        if ray_import:
            from ray.tune.schedulers import ASHAScheduler

            scheduler = ASHAScheduler(**params)
    if use_ray:
        try:
            from ray import tune
        except ImportError:
            raise ImportError(
                "Failed to import ray tune. "
                "Please install ray[tune] or set use_ray=False"
            )
        _use_ray = True
        return tune.run(
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
        )

    # simple sequential run without using tune.run() from ray
    time_start = time.time()
    _use_ray = False
    if scheduler:
        scheduler.set_search_properties(metric=metric, mode=mode)
    from .trial_runner import SequentialTrialRunner

    global _runner
    _runner = SequentialTrialRunner(
        search_alg=search_alg,
        scheduler=scheduler,
        metric=metric,
        mode=mode,
    )
    num_trials = 0
    if time_budget_s is None:
        time_budget_s = np.inf
    fail = 0
    ub = (len(evaluated_rewards) if evaluated_rewards else 0) + max_failure
    while (
        time.time() - time_start < time_budget_s
        and (num_samples < 0 or num_trials < num_samples)
        and fail < ub
    ):
        trial_to_run = _runner.step()
        if trial_to_run:
            num_trials += 1
            if verbose:
                logger.info(f"trial {num_trials} config: {trial_to_run.config}")
            result = evaluation_function(trial_to_run.config)
            if result is not None:
                if isinstance(result, dict):
                    report(**result)
                else:
                    report(_metric=result)
            _runner.stop_trial(trial_to_run)
            fail = 0
        else:
            fail += 1  # break with ub consecutive failures
    if fail == ub:
        logger.warning(
            f"fail to sample a trial for {max_failure} times in a row, stopping."
        )
    if verbose > 0:
        logger.handlers.clear()
    return ExperimentAnalysis(_runner.get_trials(), metric=metric, mode=mode)
