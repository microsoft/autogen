'''!
 * Copyright (c) 2020-2021 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in the
 * project root for license information.
'''
from typing import Optional, Union, List, Callable, Tuple
import numpy as np
import datetime
import time
try:
    from ray.tune.analysis import ExperimentAnalysis as EA
except ImportError:
    from .analysis import ExperimentAnalysis as EA
import logging
logger = logging.getLogger(__name__)


_use_ray = True
_runner = None
_verbose = 0
_running_trial = None
_training_iteration = 0


class ExperimentAnalysis(EA):
    '''Class for storing the experiment results
    '''

    def __init__(self, trials, metric, mode):
        try:
            super().__init__(self, None, trials, metric, mode)
        except (TypeError, ValueError):
            self.trials = trials
            self.default_metric = metric or '_default_anonymous_metric'
            self.default_mode = mode


def report(_metric=None, **kwargs):
    '''A function called by the HPO application to report final or intermediate
    results.

    Example:

    .. code-block:: python

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
                'x': tune.qloguniform(lower=1, upper=1000000, q=1),
                'y': tune.randint(lower=1, upper=1000000)
            },
            metric='metric2minimize', mode='min',
            num_samples=1000000, time_budget_s=60, use_ray=False)

        print(analysis.trials[-1].last_result)

    Args:
        _metric: Optional default anonymous metric for ``tune.report(value)``.
            (For compatibility with ray.tune.report)
        **kwargs: Any key value pair to be reported.
    '''
    global _use_ray
    global _verbose
    global _running_trial
    global _training_iteration
    if _use_ray:
        from ray import tune
        return tune.report(_metric, **kwargs)
    else:
        result = kwargs
        if _verbose == 2:
            logger.info(f"result: {kwargs}")
        if _metric:
            result['_default_anonymous_metric'] = _metric
        trial = _runner.running_trial
        if _running_trial == trial:
            _training_iteration += 1
        else:
            _training_iteration = 0
            _running_trial = trial
        result["training_iteration"] = _training_iteration
        result['config'] = trial.config
        for key, value in trial.config.items():
            result['config/' + key] = value
        _runner.process_trial_result(_runner.running_trial, result)
        result['time_total_s'] = trial.last_update_time - trial.start_time
        if _verbose > 2:
            logger.info(f"result: {result}")
        if _runner.running_trial.is_finished():
            return None
        else:
            return True


def run(training_function,
        config: Optional[dict] = None,
        points_to_evaluate: Optional[List[dict]] = None,
        low_cost_partial_config: Optional[dict] = None,
        cat_hp_cost: Optional[dict] = None,
        metric: Optional[str] = None,
        mode: Optional[str] = None,
        time_budget_s: Union[int, float, datetime.timedelta] = None,
        prune_attr: Optional[str] = None,
        min_resource: Optional[float] = None,
        max_resource: Optional[float] = None,
        reduction_factor: Optional[float] = None,
        report_intermediate_result: Optional[bool] = False,
        search_alg=None,
        verbose: Optional[int] = 2,
        local_dir: Optional[str] = None,
        num_samples: Optional[int] = 1,
        resources_per_trial: Optional[dict] = None,
        config_constraints: Optional[
            List[Tuple[Callable[[dict], float], str, float]]] = None,
        metric_constraints: Optional[
            List[Tuple[str, str, float]]] = None,
        use_ray: Optional[bool] = False):
    '''The trigger for HPO.

    Example:

    .. code-block:: python

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
                'x': tune.qloguniform(lower=1, upper=1000000, q=1),
                'y': tune.randint(lower=1, upper=1000000)
            },
            metric='metric2minimize', mode='min',
            num_samples=-1, time_budget_s=60, use_ray=False)

        print(analysis.trials[-1].last_result)

    Args:
        training_function: A user-defined training function.
        config: A dictionary to specify the search space.
        points_to_evaluate: A list of initial hyperparameter
            configurations to run first.
        low_cost_partial_config: A dictionary from a subset of
            controlled dimensions to the initial low-cost values.
            e.g.,

            .. code-block:: python

                {'n_estimators': 4, 'max_leaves': 4}

        cat_hp_cost: A dictionary from a subset of categorical dimensions
            to the relative cost of each choice.
            e.g.,

            .. code-block:: python

                {'tree_method': [1, 1, 2]}

            i.e., the relative cost of the
            three choices of 'tree_method' is 1, 1 and 2 respectively
        metric: A string of the metric name to optimize for.
        mode: A string in ['min', 'max'] to specify the objective as
            minimization or maximization.
        time_budget_s: A float of the time budget in seconds.
        prune_attr: A string of the attribute used for pruning.
            Not necessarily in space.
            When prune_attr is in space, it is a hyperparameter, e.g.,
            'n_iters', and the best value is unknown.
            When prune_attr is not in space, it is a resource dimension,
            e.g., 'sample_size', and the peak performance is assumed
            to be at the max_resource.
        min_resource: A float of the minimal resource to use for the
            prune_attr; only valid if prune_attr is not in space.
        max_resource: A float of the maximal resource to use for the
            prune_attr; only valid if prune_attr is not in space.
        reduction_factor: A float of the reduction factor used for incremental
            pruning.
        report_intermediate_result: A boolean of whether intermediate results
            are reported. If so, early stopping and pruning can be used.
        search_alg: An instance of BlendSearch as the search algorithm
            to be used. The same instance can be used for iterative tuning.
            e.g.,

            .. code-block:: python

                from flaml import BlendSearch
                algo = BlendSearch(metric='val_loss', mode='min',
                        space=search_space,
                        low_cost_partial_config=low_cost_partial_config)
                for i in range(10):
                    analysis = tune.run(compute_with_config,
                        search_alg=algo, use_ray=False)
                    print(analysis.trials[-1].last_result)

        verbose: 0, 1, 2, or 3. Verbosity mode for ray if ray backend is used.
            0 = silent, 1 = only status updates, 2 = status and brief trial
            results, 3 = status and detailed trial results. Defaults to 2.
        local_dir: A string of the local dir to save ray logs if ray backend is
            used; or a local dir to save the tuning log.
        num_samples: An integer of the number of configs to try. Defaults to 1.
        resources_per_trial: A dictionary of the hardware resources to allocate
            per trial, e.g., `{'cpu': 1}`. Only valid when using ray backend.
        config_constraints: A list of config constraints to be satisfied.
            e.g.,

            .. code-block: python

                config_constraints = [(mem_size, '<=', 1024**3)]

            mem_size is a function which produces a float number for the bytes
            needed for a config.
            It is used to skip configs which do not fit in memory.
        metric_constraints: A list of metric constraints to be satisfied.
            e.g., `['precision', '>=', 0.9]`
        use_ray: A boolean of whether to use ray as the backend
    '''
    global _use_ray
    global _verbose
    if not use_ray:
        _verbose = verbose
        if verbose > 0:
            import os
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
                logger.addHandler(logging.FileHandler(local_dir + '/tune_' + str(
                    datetime.datetime.now()).replace(':', '-') + '.log'))
            elif not logger.handlers:
                # Add the console handler.
                _ch = logging.StreamHandler()
                logger_formatter = logging.Formatter(
                    '[%(name)s: %(asctime)s] {%(lineno)d} %(levelname)s - %(message)s',
                    '%m-%d %H:%M:%S')
                _ch.setFormatter(logger_formatter)
                logger.addHandler(_ch)
            if verbose <= 2:
                logger.setLevel(logging.INFO)
            else:
                logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.CRITICAL)

    if search_alg is None:
        from ..searcher.blendsearch import BlendSearch
        search_alg = BlendSearch(
            metric=metric or '_default_anonymous_metric', mode=mode,
            space=config,
            points_to_evaluate=points_to_evaluate,
            low_cost_partial_config=low_cost_partial_config,
            cat_hp_cost=cat_hp_cost,
            prune_attr=prune_attr,
            min_resource=min_resource, max_resource=max_resource,
            reduction_factor=reduction_factor,
            config_constraints=config_constraints,
            metric_constraints=metric_constraints)
    if time_budget_s:
        search_alg.set_search_properties(metric, mode, config={
            'time_budget_s': time_budget_s})
    scheduler = None
    if report_intermediate_result:
        params = {}
        # scheduler resource_dimension=prune_attr
        if prune_attr:
            params['time_attr'] = prune_attr
        if max_resource:
            params['max_t'] = max_resource
        if min_resource:
            params['grace_period'] = min_resource
        if reduction_factor:
            params['reduction_factor'] = reduction_factor
        try:
            from ray.tune.schedulers import ASHAScheduler
            scheduler = ASHAScheduler(**params)
        except ImportError:
            pass
    if use_ray:
        try:
            from ray import tune
        except ImportError:
            raise ImportError("Failed to import ray tune. "
                              "Please install ray[tune] or set use_ray=False")
        _use_ray = True
        return tune.run(training_function,
                        metric=metric, mode=mode,
                        search_alg=search_alg,
                        scheduler=scheduler,
                        time_budget_s=time_budget_s,
                        verbose=verbose, local_dir=local_dir,
                        num_samples=num_samples,
                        resources_per_trial=resources_per_trial)

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
    while time.time() - time_start < time_budget_s and (
            num_samples < 0 or num_trials < num_samples):
        trial_to_run = _runner.step()
        if trial_to_run:
            num_trials += 1
            if verbose:
                logger.info(f'trial {num_trials} config: {trial_to_run.config}')
            result = training_function(trial_to_run.config)
            if result is not None:
                if isinstance(result, dict):
                    tune.report(**result)
                else:
                    tune.report(_metric=result)
            _runner.stop_trial(trial_to_run)
    if verbose > 0:
        logger.handlers.clear()
    return ExperimentAnalysis(_runner.get_trials(), metric=metric, mode=mode)
