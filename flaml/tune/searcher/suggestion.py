# Copyright 2020 The Ray Authors.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This source file is adapted here because ray does not fully support Windows.

# Copyright (c) Microsoft Corporation.
import time
import functools
import warnings
import copy
import numpy as np
import logging
from typing import Any, Dict, Optional, Union, List, Tuple, Callable
import pickle
from .variant_generator import parse_spec_vars
from ..sample import (
    Categorical,
    Domain,
    Float,
    Integer,
    LogUniform,
    Quantized,
    Uniform,
)
from ..trial import flatten_dict, unflatten_dict
from collections import defaultdict

logger = logging.getLogger(__name__)

UNRESOLVED_SEARCH_SPACE = str(
    "You passed a `{par}` parameter to {cls} that contained unresolved search "
    "space definitions. {cls} should however be instantiated with fully "
    "configured search spaces only. To use Ray Tune's automatic search space "
    "conversion, pass the space definition as part of the `config` argument "
    "to `tune.run()` instead."
)

UNDEFINED_SEARCH_SPACE = str(
    "Trying to sample a configuration from {cls}, but no search "
    "space has been defined. Either pass the `{space}` argument when "
    "instantiating the search algorithm, or pass a `config` to "
    "`tune.run()`."
)

UNDEFINED_METRIC_MODE = str(
    "Trying to sample a configuration from {cls}, but the `metric` "
    "({metric}) or `mode` ({mode}) parameters have not been set. "
    "Either pass these arguments when instantiating the search algorithm, "
    "or pass them to `tune.run()`."
)


class Searcher:
    """Abstract class for wrapping suggesting algorithms.
    Custom algorithms can extend this class easily by overriding the
    `suggest` method provide generated parameters for the trials.
    Any subclass that implements ``__init__`` must also call the
    constructor of this class: ``super(Subclass, self).__init__(...)``.
    To track suggestions and their corresponding evaluations, the method
    `suggest` will be passed a trial_id, which will be used in
    subsequent notifications.
    Not all implementations support multi objectives.
    Args:
        metric (str or list): The training result objective value attribute. If
            list then list of training result objective value attributes
        mode (str or list): If string One of {min, max}. If list then
            list of max and min, determines whether objective is minimizing
            or maximizing the metric attribute. Must match type of metric.

    ```python
    class ExampleSearch(Searcher):
        def __init__(self, metric="mean_loss", mode="min", **kwargs):
            super(ExampleSearch, self).__init__(
                metric=metric, mode=mode, **kwargs)
            self.optimizer = Optimizer()
            self.configurations = {}
        def suggest(self, trial_id):
            configuration = self.optimizer.query()
            self.configurations[trial_id] = configuration
        def on_trial_complete(self, trial_id, result, **kwargs):
            configuration = self.configurations[trial_id]
            if result and self.metric in result:
                self.optimizer.update(configuration, result[self.metric])
    tune.run(trainable_function, search_alg=ExampleSearch())
    ```

    """

    FINISHED = "FINISHED"
    CKPT_FILE_TMPL = "searcher-state-{}.pkl"

    def __init__(
        self,
        metric: Optional[str] = None,
        mode: Optional[str] = None,
        max_concurrent: Optional[int] = None,
        use_early_stopped_trials: Optional[bool] = None,
    ):
        self._metric = metric
        self._mode = mode

        if not mode or not metric:
            # Early return to avoid assertions
            return

        assert isinstance(metric, type(mode)), "metric and mode must be of the same type"
        if isinstance(mode, str):
            assert mode in ["min", "max"], "if `mode` is a str must be 'min' or 'max'!"
        elif isinstance(mode, list):
            assert len(mode) == len(metric), "Metric and mode must be the same length"
            assert all(mod in ["min", "max", "obs"] for mod in mode), "All of mode must be 'min' or 'max' or 'obs'!"
        else:
            raise ValueError("Mode must either be a list or string")

    def set_search_properties(self, metric: Optional[str], mode: Optional[str], config: Dict) -> bool:
        """Pass search properties to searcher.
        This method acts as an alternative to instantiating search algorithms
        with their own specific search spaces. Instead they can accept a
        Tune config through this method. A searcher should return ``True``
        if setting the config was successful, or ``False`` if it was
        unsuccessful, e.g. when the search space has already been set.
        Args:
            metric (str): Metric to optimize
            mode (str): One of ["min", "max"]. Direction to optimize.
            config (dict): Tune config dict.
        """
        return False

    def on_trial_result(self, trial_id: str, result: Dict):
        """Optional notification for result during training.
        Note that by default, the result dict may include NaNs or
        may not include the optimization metric. It is up to the
        subclass implementation to preprocess the result to
        avoid breaking the optimization process.
        Args:
            trial_id (str): A unique string ID for the trial.
            result (dict): Dictionary of metrics for current training progress.
                Note that the result dict may include NaNs or
                may not include the optimization metric. It is up to the
                subclass implementation to preprocess the result to
                avoid breaking the optimization process.
        """
        pass

    @property
    def metric(self) -> str:
        """The training result objective value attribute."""
        return self._metric

    @property
    def mode(self) -> str:
        """Specifies if minimizing or maximizing the metric."""
        return self._mode


class ConcurrencyLimiter(Searcher):
    """A wrapper algorithm for limiting the number of concurrent trials.
    Args:
        searcher (Searcher): Searcher object that the
            ConcurrencyLimiter will manage.
        max_concurrent (int): Maximum concurrent samples from the underlying
            searcher.
        batch (bool): Whether to wait for all concurrent samples
            to finish before updating the underlying searcher.
    Example:
    ```python
    from ray.tune.suggest import ConcurrencyLimiter  # ray version < 2
    search_alg = HyperOptSearch(metric="accuracy")
    search_alg = ConcurrencyLimiter(search_alg, max_concurrent=2)
    tune.run(trainable, search_alg=search_alg)
    ```
    """

    def __init__(self, searcher: Searcher, max_concurrent: int, batch: bool = False):
        assert type(max_concurrent) is int and max_concurrent > 0
        self.searcher = searcher
        self.max_concurrent = max_concurrent
        self.batch = batch
        self.live_trials = set()
        self.cached_results = {}
        super(ConcurrencyLimiter, self).__init__(metric=self.searcher.metric, mode=self.searcher.mode)

    def suggest(self, trial_id: str) -> Optional[Dict]:
        assert trial_id not in self.live_trials, f"Trial ID {trial_id} must be unique: already found in set."
        if len(self.live_trials) >= self.max_concurrent:
            logger.debug(
                f"Not providing a suggestion for {trial_id} due to " "concurrency limit: %s/%s.",
                len(self.live_trials),
                self.max_concurrent,
            )
            return

        suggestion = self.searcher.suggest(trial_id)
        if suggestion not in (None, Searcher.FINISHED):
            self.live_trials.add(trial_id)
        return suggestion

    def on_trial_complete(self, trial_id: str, result: Optional[Dict] = None, error: bool = False):
        if trial_id not in self.live_trials:
            return
        elif self.batch:
            self.cached_results[trial_id] = (result, error)
            if len(self.cached_results) == self.max_concurrent:
                # Update the underlying searcher once the
                # full batch is completed.
                for trial_id, (result, error) in self.cached_results.items():
                    self.searcher.on_trial_complete(trial_id, result=result, error=error)
                    self.live_trials.remove(trial_id)
                self.cached_results = {}
            else:
                return
        else:
            self.searcher.on_trial_complete(trial_id, result=result, error=error)
            self.live_trials.remove(trial_id)

    def get_state(self) -> Dict:
        state = self.__dict__.copy()
        del state["searcher"]
        return copy.deepcopy(state)

    def set_state(self, state: Dict):
        self.__dict__.update(state)

    def save(self, checkpoint_path: str):
        self.searcher.save(checkpoint_path)

    def restore(self, checkpoint_path: str):
        self.searcher.restore(checkpoint_path)

    def on_pause(self, trial_id: str):
        self.searcher.on_pause(trial_id)

    def on_unpause(self, trial_id: str):
        self.searcher.on_unpause(trial_id)

    def set_search_properties(self, metric: Optional[str], mode: Optional[str], config: Dict) -> bool:
        return self.searcher.set_search_properties(metric, mode, config)


try:
    import optuna as ot
    from optuna.distributions import BaseDistribution as OptunaDistribution
    from optuna.samplers import BaseSampler
    from optuna.trial import TrialState as OptunaTrialState
    from optuna.trial import Trial as OptunaTrial
except ImportError:
    ot = None
    OptunaDistribution = None
    BaseSampler = None
    OptunaTrialState = None
    OptunaTrial = None

DEFAULT_METRIC = "_metric"

TRAINING_ITERATION = "training_iteration"

DEFINE_BY_RUN_WARN_THRESHOLD_S = 1


def validate_warmstart(
    parameter_names: List[str],
    points_to_evaluate: List[Union[List, Dict]],
    evaluated_rewards: List,
    validate_point_name_lengths: bool = True,
):
    """Generic validation of a Searcher's warm start functionality.
    Raises exceptions in case of type and length mismatches between
    parameters.
    If ``validate_point_name_lengths`` is False, the equality of lengths
    between ``points_to_evaluate`` and ``parameter_names`` will not be
    validated.
    """
    if points_to_evaluate:
        if not isinstance(points_to_evaluate, list):
            raise TypeError("points_to_evaluate expected to be a list, got {}.".format(type(points_to_evaluate)))
        for point in points_to_evaluate:
            if not isinstance(point, (dict, list)):
                raise TypeError(f"points_to_evaluate expected to include list or dict, " f"got {point}.")

            if validate_point_name_lengths and (not len(point) == len(parameter_names)):
                raise ValueError(
                    "Dim of point {}".format(point)
                    + " and parameter_names {}".format(parameter_names)
                    + " do not match."
                )

    if points_to_evaluate and evaluated_rewards:
        if not isinstance(evaluated_rewards, list):
            raise TypeError("evaluated_rewards expected to be a list, got {}.".format(type(evaluated_rewards)))
        if not len(evaluated_rewards) == len(points_to_evaluate):
            raise ValueError(
                "Dim of evaluated_rewards {}".format(evaluated_rewards)
                + " and points_to_evaluate {}".format(points_to_evaluate)
                + " do not match."
            )


class _OptunaTrialSuggestCaptor:
    """Utility to capture returned values from Optuna's suggest_ methods.

    This will wrap around the ``optuna.Trial` object and decorate all
    `suggest_` callables with a function capturing the returned value,
    which will be saved in the ``captured_values`` dict.
    """

    def __init__(self, ot_trial: OptunaTrial) -> None:
        self.ot_trial = ot_trial
        self.captured_values: Dict[str, Any] = {}

    def _get_wrapper(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # name is always the first arg for suggest_ methods
            name = kwargs.get("name", args[0])
            ret = func(*args, **kwargs)
            self.captured_values[name] = ret
            return ret

        return wrapper

    def __getattr__(self, item_name: str) -> Any:
        item = getattr(self.ot_trial, item_name)
        if item_name.startswith("suggest_") and callable(item):
            return self._get_wrapper(item)
        return item


class OptunaSearch(Searcher):
    """A wrapper around Optuna to provide trial suggestions.

    `Optuna <https://optuna.org/>`_ is a hyperparameter optimization library.
    In contrast to other libraries, it employs define-by-run style
    hyperparameter definitions.

    This Searcher is a thin wrapper around Optuna's search algorithms.
    You can pass any Optuna sampler, which will be used to generate
    hyperparameter suggestions.

    Multi-objective optimization is supported.

    Args:
        space: Hyperparameter search space definition for
            Optuna's sampler. This can be either a dict with
            parameter names as keys and ``optuna.distributions`` as values,
            or a Callable - in which case, it should be a define-by-run
            function using ``optuna.trial`` to obtain the hyperparameter
            values. The function should return either a dict of
            constant values with names as keys, or None.
            For more information, see https://optuna.readthedocs.io\
/en/stable/tutorial/10_key_features/002_configurations.html.

            Warning - No actual computation should take place in the define-by-run
            function. Instead, put the training logic inside the function
            or class trainable passed to ``tune.run``.

        metric: The training result objective value attribute. If
            None but a mode was passed, the anonymous metric ``_metric``
            will be used per default. Can be a list of metrics for
            multi-objective optimization.
        mode: One of {min, max}. Determines whether objective is
            minimizing or maximizing the metric attribute. Can be a list of
            modes for multi-objective optimization (corresponding to
            ``metric``).
        points_to_evaluate: Initial parameter suggestions to be run
            first. This is for when you already have some good parameters
            you want to run first to help the algorithm make better suggestions
            for future parameters. Needs to be a list of dicts containing the
            configurations.
        sampler: Optuna sampler used to
            draw hyperparameter configurations. Defaults to ``MOTPESampler``
            for multi-objective optimization with Optuna<2.9.0, and
            ``TPESampler`` in every other case.

            Warning: Please note that with Optuna 2.10.0 and earlier
                default ``MOTPESampler``/``TPESampler`` suffer
                from performance issues when dealing with a large number of
                completed trials (approx. >100). This will manifest as
                a delay when suggesting new configurations.
                This is an Optuna issue and may be fixed in a future
                Optuna release.

        seed: Seed to initialize sampler with. This parameter is only
            used when ``sampler=None``. In all other cases, the sampler
            you pass should be initialized with the seed already.
        evaluated_rewards: If you have previously evaluated the
            parameters passed in as points_to_evaluate you can avoid
            re-running those trials by passing in the reward attributes
            as a list so the optimiser can be told the results without
            needing to re-compute the trial. Must be the same length as
            points_to_evaluate.

            Warning - When using ``evaluated_rewards``, the search space ``space``
            must be provided as a dict with parameter names as
            keys and ``optuna.distributions`` instances as values. The
            define-by-run search space definition is not yet supported with
            this functionality.

    Tune automatically converts search spaces to Optuna's format:

    ```python
    from ray.tune.suggest.optuna import OptunaSearch

    config = {
        "a": tune.uniform(6, 8)
        "b": tune.loguniform(1e-4, 1e-2)
    }

    optuna_search = OptunaSearch(
        metric="loss",
        mode="min")

    tune.run(trainable, config=config, search_alg=optuna_search)
    ```

    If you would like to pass the search space manually, the code would
    look like this:

    ```python
    from ray.tune.suggest.optuna import OptunaSearch
    import optuna

    space = {
        "a": optuna.distributions.UniformDistribution(6, 8),
        "b": optuna.distributions.LogUniformDistribution(1e-4, 1e-2),
    }

    optuna_search = OptunaSearch(
        space,
        metric="loss",
        mode="min")

    tune.run(trainable, search_alg=optuna_search)

    # Equivalent Optuna define-by-run function approach:

    def define_search_space(trial: optuna.Trial):
        trial.suggest_float("a", 6, 8)
        trial.suggest_float("b", 1e-4, 1e-2, log=True)
        # training logic goes into trainable, this is just
        # for search space definition

    optuna_search = OptunaSearch(
        define_search_space,
        metric="loss",
        mode="min")

    tune.run(trainable, search_alg=optuna_search)
    ```

    Multi-objective optimization is supported:

    ```python
    from ray.tune.suggest.optuna import OptunaSearch
    import optuna

    space = {
        "a": optuna.distributions.UniformDistribution(6, 8),
        "b": optuna.distributions.LogUniformDistribution(1e-4, 1e-2),
    }

    # Note you have to specify metric and mode here instead of
    # in tune.run
    optuna_search = OptunaSearch(
        space,
        metric=["loss1", "loss2"],
        mode=["min", "max"])

    # Do not specify metric and mode here!
    tune.run(
        trainable,
        search_alg=optuna_search
    )
    ```

    You can pass configs that will be evaluated first using
    ``points_to_evaluate``:

    ```python
    from ray.tune.suggest.optuna import OptunaSearch
    import optuna

    space = {
        "a": optuna.distributions.UniformDistribution(6, 8),
        "b": optuna.distributions.LogUniformDistribution(1e-4, 1e-2),
    }

    optuna_search = OptunaSearch(
        space,
        points_to_evaluate=[{"a": 6.5, "b": 5e-4}, {"a": 7.5, "b": 1e-3}]
        metric="loss",
        mode="min")

    tune.run(trainable, search_alg=optuna_search)
    ```

    Avoid re-running evaluated trials by passing the rewards together with
    `points_to_evaluate`:

    ```python
    from ray.tune.suggest.optuna import OptunaSearch
    import optuna

    space = {
        "a": optuna.distributions.UniformDistribution(6, 8),
        "b": optuna.distributions.LogUniformDistribution(1e-4, 1e-2),
    }

    optuna_search = OptunaSearch(
        space,
        points_to_evaluate=[{"a": 6.5, "b": 5e-4}, {"a": 7.5, "b": 1e-3}]
        evaluated_rewards=[0.89, 0.42]
        metric="loss",
        mode="min")

    tune.run(trainable, search_alg=optuna_search)
    ```

    """

    def __init__(
        self,
        space: Optional[
            Union[
                Dict[str, "OptunaDistribution"],
                List[Tuple],
                Callable[["OptunaTrial"], Optional[Dict[str, Any]]],
            ]
        ] = None,
        metric: Optional[Union[str, List[str]]] = None,
        mode: Optional[Union[str, List[str]]] = None,
        points_to_evaluate: Optional[List[Dict]] = None,
        sampler: Optional["BaseSampler"] = None,
        seed: Optional[int] = None,
        evaluated_rewards: Optional[List] = None,
    ):
        assert ot is not None, "Optuna must be installed! Run `pip install optuna`."
        super(OptunaSearch, self).__init__(metric=metric, mode=mode)

        if isinstance(space, dict) and space:
            resolved_vars, domain_vars, grid_vars = parse_spec_vars(space)
            if domain_vars or grid_vars:
                logger.warning(UNRESOLVED_SEARCH_SPACE.format(par="space", cls=type(self).__name__))
                space = self.convert_search_space(space)
            else:
                # Flatten to support nested dicts
                space = flatten_dict(space, "/")

        self._space = space

        self._points_to_evaluate = points_to_evaluate or []
        self._evaluated_rewards = evaluated_rewards

        self._study_name = "optuna"  # Fixed study name for in-memory storage

        if sampler and seed:
            logger.warning(
                "You passed an initialized sampler to `OptunaSearch`. The "
                "`seed` parameter has to be passed to the sampler directly "
                "and will be ignored."
            )
        elif sampler:
            assert isinstance(sampler, BaseSampler), (
                "You can only pass an instance of " "`optuna.samplers.BaseSampler` " "as a sampler to `OptunaSearcher`."
            )

        self._sampler = sampler
        self._seed = seed

        self._completed_trials = set()

        self._ot_trials = {}
        self._ot_study = None
        if self._space:
            self._setup_study(mode)

    def _setup_study(self, mode: Union[str, list]):
        if self._metric is None and self._mode:
            if isinstance(self._mode, list):
                raise ValueError(
                    "If ``mode`` is a list (multi-objective optimization " "case), ``metric`` must be defined."
                )
            # If only a mode was passed, use anonymous metric
            self._metric = DEFAULT_METRIC

        pruner = ot.pruners.NopPruner()
        storage = ot.storages.InMemoryStorage()
        try:
            from packaging import version
        except ImportError:
            raise ImportError("To use BlendSearch, run: pip install flaml[blendsearch]")
        if self._sampler:
            sampler = self._sampler
        elif isinstance(mode, list) and version.parse(ot.__version__) < version.parse("2.9.0"):
            # MOTPESampler deprecated in Optuna>=2.9.0
            sampler = ot.samplers.MOTPESampler(seed=self._seed)
        else:
            sampler = ot.samplers.TPESampler(seed=self._seed)

        if isinstance(mode, list):
            study_direction_args = dict(
                directions=["minimize" if m == "min" else "maximize" for m in mode],
            )
        else:
            study_direction_args = dict(
                direction="minimize" if mode == "min" else "maximize",
            )

        self._ot_study = ot.study.create_study(
            storage=storage,
            sampler=sampler,
            pruner=pruner,
            study_name=self._study_name,
            load_if_exists=True,
            **study_direction_args,
        )

        if self._points_to_evaluate:
            validate_warmstart(
                self._space,
                self._points_to_evaluate,
                self._evaluated_rewards,
                validate_point_name_lengths=not callable(self._space),
            )
            if self._evaluated_rewards:
                for point, reward in zip(self._points_to_evaluate, self._evaluated_rewards):
                    self.add_evaluated_point(point, reward)
            else:
                for point in self._points_to_evaluate:
                    self._ot_study.enqueue_trial(point)

    def set_search_properties(self, metric: Optional[str], mode: Optional[str], config: Dict, **spec) -> bool:
        if self._space:
            return False
        space = self.convert_search_space(config)
        self._space = space
        if metric:
            self._metric = metric
        if mode:
            self._mode = mode

        self._setup_study(self._mode)
        return True

    def _suggest_from_define_by_run_func(
        self,
        func: Callable[["OptunaTrial"], Optional[Dict[str, Any]]],
        ot_trial: "OptunaTrial",
    ) -> Dict:
        captor = _OptunaTrialSuggestCaptor(ot_trial)
        time_start = time.time()
        ret = func(captor)
        time_taken = time.time() - time_start
        if time_taken > DEFINE_BY_RUN_WARN_THRESHOLD_S:
            warnings.warn(
                "Define-by-run function passed in the `space` argument "
                f"took {time_taken} seconds to "
                "run. Ensure that actual computation, training takes "
                "place inside Tune's train functions or Trainables "
                "passed to `tune.run`."
            )
        if ret is not None:
            if not isinstance(ret, dict):
                raise TypeError(
                    "The return value of the define-by-run function "
                    "passed in the `space` argument should be "
                    "either None or a `dict` with `str` keys. "
                    f"Got {type(ret)}."
                )
            if not all(isinstance(k, str) for k in ret.keys()):
                raise TypeError(
                    "At least one of the keys in the dict returned by the "
                    "define-by-run function passed in the `space` argument "
                    "was not a `str`."
                )
        return {**captor.captured_values, **ret} if ret else captor.captured_values

    def suggest(self, trial_id: str) -> Optional[Dict]:
        if not self._space:
            raise RuntimeError(UNDEFINED_SEARCH_SPACE.format(cls=self.__class__.__name__, space="space"))
        if not self._metric or not self._mode:
            raise RuntimeError(
                UNDEFINED_METRIC_MODE.format(cls=self.__class__.__name__, metric=self._metric, mode=self._mode)
            )
        if callable(self._space):
            # Define-by-run case
            if trial_id not in self._ot_trials:
                self._ot_trials[trial_id] = self._ot_study.ask()

            ot_trial = self._ot_trials[trial_id]

            params = self._suggest_from_define_by_run_func(self._space, ot_trial)
        else:
            # Use Optuna ask interface (since version 2.6.0)
            if trial_id not in self._ot_trials:
                self._ot_trials[trial_id] = self._ot_study.ask(fixed_distributions=self._space)
            ot_trial = self._ot_trials[trial_id]
            params = ot_trial.params

        return unflatten_dict(params)

    def on_trial_result(self, trial_id: str, result: Dict):
        if isinstance(self.metric, list):
            # Optuna doesn't support incremental results
            # for multi-objective optimization
            return
        if trial_id in self._completed_trials:
            logger.warning(
                f"Received additional result for trial {trial_id}, but " f"it already finished. Result: {result}"
            )
            return
        metric = result[self.metric]
        step = result[TRAINING_ITERATION]
        ot_trial = self._ot_trials[trial_id]
        ot_trial.report(metric, step)

    def on_trial_complete(self, trial_id: str, result: Optional[Dict] = None, error: bool = False):
        if trial_id in self._completed_trials:
            logger.warning(
                f"Received additional completion for trial {trial_id}, but " f"it already finished. Result: {result}"
            )
            return

        ot_trial = self._ot_trials[trial_id]

        if result:
            if isinstance(self.metric, list):
                val = [result.get(metric, None) for metric in self.metric]
            else:
                val = result.get(self.metric, None)
        else:
            val = None
        ot_trial_state = OptunaTrialState.COMPLETE
        if val is None:
            if error:
                ot_trial_state = OptunaTrialState.FAIL
            else:
                ot_trial_state = OptunaTrialState.PRUNED
        try:
            self._ot_study.tell(ot_trial, val, state=ot_trial_state)
        except Exception as exc:
            logger.warning(exc)  # E.g. if NaN was reported

        self._completed_trials.add(trial_id)

    def add_evaluated_point(
        self,
        parameters: Dict,
        value: float,
        error: bool = False,
        pruned: bool = False,
        intermediate_values: Optional[List[float]] = None,
    ):
        if not self._space:
            raise RuntimeError(UNDEFINED_SEARCH_SPACE.format(cls=self.__class__.__name__, space="space"))
        if not self._metric or not self._mode:
            raise RuntimeError(
                UNDEFINED_METRIC_MODE.format(cls=self.__class__.__name__, metric=self._metric, mode=self._mode)
            )
        if callable(self._space):
            raise TypeError(
                "Define-by-run function passed in `space` argument is not "
                "yet supported when using `evaluated_rewards`. Please provide "
                "an `OptunaDistribution` dict or pass a Ray Tune "
                "search space to `tune.run()`."
            )

        ot_trial_state = OptunaTrialState.COMPLETE
        if error:
            ot_trial_state = OptunaTrialState.FAIL
        elif pruned:
            ot_trial_state = OptunaTrialState.PRUNED

        if intermediate_values:
            intermediate_values_dict = {i: value for i, value in enumerate(intermediate_values)}
        else:
            intermediate_values_dict = None

        trial = ot.trial.create_trial(
            state=ot_trial_state,
            value=value,
            params=parameters,
            distributions=self._space,
            intermediate_values=intermediate_values_dict,
        )

        self._ot_study.add_trial(trial)

    def save(self, checkpoint_path: str):
        save_object = (
            self._sampler,
            self._ot_trials,
            self._ot_study,
            self._points_to_evaluate,
            self._evaluated_rewards,
        )
        with open(checkpoint_path, "wb") as outputFile:
            pickle.dump(save_object, outputFile)

    def restore(self, checkpoint_path: str):
        with open(checkpoint_path, "rb") as inputFile:
            save_object = pickle.load(inputFile)
        if len(save_object) == 5:
            (
                self._sampler,
                self._ot_trials,
                self._ot_study,
                self._points_to_evaluate,
                self._evaluated_rewards,
            ) = save_object
        else:
            # Backwards compatibility
            (
                self._sampler,
                self._ot_trials,
                self._ot_study,
                self._points_to_evaluate,
            ) = save_object

    @staticmethod
    def convert_search_space(spec: Dict) -> Dict[str, Any]:
        resolved_vars, domain_vars, grid_vars = parse_spec_vars(spec)

        if not domain_vars and not grid_vars:
            return {}

        if grid_vars:
            raise ValueError("Grid search parameters cannot be automatically converted " "to an Optuna search space.")

        # Flatten and resolve again after checking for grid search.
        spec = flatten_dict(spec, prevent_delimiter=True)
        resolved_vars, domain_vars, grid_vars = parse_spec_vars(spec)

        def resolve_value(domain: Domain) -> ot.distributions.BaseDistribution:
            quantize = None

            sampler = domain.get_sampler()
            if isinstance(sampler, Quantized):
                quantize = sampler.q
                sampler = sampler.sampler
                if isinstance(sampler, LogUniform):
                    logger.warning(
                        "Optuna does not handle quantization in loguniform "
                        "sampling. The parameter will be passed but it will "
                        "probably be ignored."
                    )

            if isinstance(domain, Float):
                if isinstance(sampler, LogUniform):
                    if quantize:
                        logger.warning(
                            "Optuna does not support both quantization and "
                            "sampling from LogUniform. Dropped quantization."
                        )
                    return ot.distributions.LogUniformDistribution(domain.lower, domain.upper)

                elif isinstance(sampler, Uniform):
                    if quantize:
                        return ot.distributions.DiscreteUniformDistribution(domain.lower, domain.upper, quantize)
                    return ot.distributions.UniformDistribution(domain.lower, domain.upper)

            elif isinstance(domain, Integer):
                if isinstance(sampler, LogUniform):
                    return ot.distributions.IntLogUniformDistribution(
                        domain.lower, domain.upper - 1, step=quantize or 1
                    )
                elif isinstance(sampler, Uniform):
                    # Upper bound should be inclusive for quantization and
                    # exclusive otherwise
                    return ot.distributions.IntUniformDistribution(
                        domain.lower,
                        domain.upper - int(bool(not quantize)),
                        step=quantize or 1,
                    )
            elif isinstance(domain, Categorical):
                if isinstance(sampler, Uniform):
                    return ot.distributions.CategoricalDistribution(domain.categories)

            raise ValueError(
                "Optuna search does not support parameters of type "
                "`{}` with samplers of type `{}`".format(type(domain).__name__, type(domain.sampler).__name__)
            )

        # Parameter name is e.g. "a/b/c" for nested dicts
        values = {"/".join(path): resolve_value(domain) for path, domain in domain_vars}

        return values
