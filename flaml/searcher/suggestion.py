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
import copy
import glob
import logging
import os
import time
from typing import Dict, Optional, Union, List, Tuple
import pickle
from .variant_generator import parse_spec_vars
from ..tune.sample import Categorical, Domain, Float, Integer, LogUniform, \
    Quantized, Uniform
from ..tune.trial import flatten_dict, unflatten_dict

logger = logging.getLogger(__name__)

UNRESOLVED_SEARCH_SPACE = str(
    "You passed a `{par}` parameter to {cls} that contained unresolved search "
    "space definitions. {cls} should however be instantiated with fully "
    "configured search spaces only. To use Ray Tune's automatic search space "
    "conversion, pass the space definition as part of the `config` argument "
    "to `tune.run()` instead.")

UNDEFINED_SEARCH_SPACE = str(
    "Trying to sample a configuration from {cls}, but no search "
    "space has been defined. Either pass the `{space}` argument when "
    "instantiating the search algorithm, or pass a `config` to "
    "`tune.run()`.")

UNDEFINED_METRIC_MODE = str(
    "Trying to sample a configuration from {cls}, but the `metric` "
    "({metric}) or `mode` ({mode}) parameters have not been set. "
    "Either pass these arguments when instantiating the search algorithm, "
    "or pass them to `tune.run()`.")


_logged = set()
_disabled = False
_periodic_log = False
_last_logged = 0.0


def log_once(key):
    """Returns True if this is the "first" call for a given key.
    Various logging settings can adjust the definition of "first".
    Example:
        >>> if log_once("some_key"):
        ...     logger.info("Some verbose logging statement")
    """

    global _last_logged

    if _disabled:
        return False
    elif key not in _logged:
        _logged.add(key)
        _last_logged = time.time()
        return True
    elif _periodic_log and time.time() - _last_logged > 60.0:
        _logged.clear()
        _last_logged = time.time()
        return False
    else:
        return False


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
    .. code-block:: python
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
    """
    FINISHED = "FINISHED"
    CKPT_FILE_TMPL = "searcher-state-{}.pkl"

    def __init__(self,
                 metric: Optional[str] = None,
                 mode: Optional[str] = None,
                 max_concurrent: Optional[int] = None,
                 use_early_stopped_trials: Optional[bool] = None):
        if use_early_stopped_trials is False:
            raise DeprecationWarning(
                "Early stopped trials are now always used. If this is a "
                "problem, file an issue: https://github.com/ray-project/ray.")
        if max_concurrent is not None:
            logger.warning(
                "DeprecationWarning: `max_concurrent` is deprecated for this "
                "search algorithm. Use tune.suggest.ConcurrencyLimiter() "
                "instead. This will raise an error in future versions of Ray.")

        self._metric = metric
        self._mode = mode

        if not mode or not metric:
            # Early return to avoid assertions
            return

        assert isinstance(
            metric, type(mode)), "metric and mode must be of the same type"
        if isinstance(mode, str):
            assert mode in ["min", "max"
                            ], "if `mode` is a str must be 'min' or 'max'!"
        elif isinstance(mode, list):
            assert len(mode) == len(
                metric), "Metric and mode must be the same length"
            assert all(mod in ["min", "max", "obs"] for mod in
                       mode), "All of mode must be 'min' or 'max' or 'obs'!"
        else:
            raise ValueError("Mode most either be a list or string")

    def set_search_properties(self, metric: Optional[str], mode: Optional[str],
                              config: Dict) -> bool:
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

    def on_trial_complete(self,
                          trial_id: str,
                          result: Optional[Dict] = None,
                          error: bool = False):
        """Notification for the completion of trial.
        Typically, this method is used for notifying the underlying
        optimizer of the result.
        Args:
            trial_id (str): A unique string ID for the trial.
            result (dict): Dictionary of metrics for current training progress.
                Note that the result dict may include NaNs or
                may not include the optimization metric. It is up to the
                subclass implementation to preprocess the result to
                avoid breaking the optimization process. Upon errors, this
                may also be None.
            error (bool): True if the training process raised an error.
        """
        raise NotImplementedError

    def suggest(self, trial_id: str) -> Optional[Dict]:
        """Queries the algorithm to retrieve the next set of parameters.
        Arguments:
            trial_id (str): Trial ID used for subsequent notifications.
        Returns:
            dict | FINISHED | None: Configuration for a trial, if possible.
                If FINISHED is returned, Tune will be notified that
                no more suggestions/configurations will be provided.
                If None is returned, Tune will skip the querying of the
                searcher for this step.
        """
        raise NotImplementedError

    def save(self, checkpoint_path: str):
        """Save state to path for this search algorithm.
        Args:
            checkpoint_path (str): File where the search algorithm
                state is saved. This path should be used later when
                restoring from file.
        Example:
        .. code-block:: python
            search_alg = Searcher(...)
            analysis = tune.run(
                cost,
                num_samples=5,
                search_alg=search_alg,
                name=self.experiment_name,
                local_dir=self.tmpdir)
            search_alg.save("./my_favorite_path.pkl")
        .. versionchanged:: 0.8.7
            Save is automatically called by `tune.run`. You can use
            `restore_from_dir` to restore from an experiment directory
            such as `~/ray_results/trainable`.
        """
        raise NotImplementedError

    def restore(self, checkpoint_path: str):
        """Restore state for this search algorithm
        Args:
            checkpoint_path (str): File where the search algorithm
                state is saved. This path should be the same
                as the one provided to "save".
        Example:
        .. code-block:: python
            search_alg.save("./my_favorite_path.pkl")
            search_alg2 = Searcher(...)
            search_alg2 = ConcurrencyLimiter(search_alg2, 1)
            search_alg2.restore(checkpoint_path)
            tune.run(cost, num_samples=5, search_alg=search_alg2)
        """
        raise NotImplementedError

    def get_state(self) -> Dict:
        raise NotImplementedError

    def set_state(self, state: Dict):
        raise NotImplementedError

    def save_to_dir(self, checkpoint_dir: str, session_str: str = "default"):
        """Automatically saves the given searcher to the checkpoint_dir.
        This is automatically used by tune.run during a Tune job.
        Args:
            checkpoint_dir (str): Filepath to experiment dir.
            session_str (str): Unique identifier of the current run
                session.
        """
        tmp_search_ckpt_path = os.path.join(checkpoint_dir,
                                            ".tmp_searcher_ckpt")
        success = True
        try:
            self.save(tmp_search_ckpt_path)
        except NotImplementedError:
            if log_once("suggest:save_to_dir"):
                logger.warning(
                    "save not implemented for Searcher. Skipping save.")
            success = False

        if success and os.path.exists(tmp_search_ckpt_path):
            os.rename(
                tmp_search_ckpt_path,
                os.path.join(checkpoint_dir,
                             self.CKPT_FILE_TMPL.format(session_str)))

    def restore_from_dir(self, checkpoint_dir: str):
        """Restores the state of a searcher from a given checkpoint_dir.
        Typically, you should use this function to restore from an
        experiment directory such as `~/ray_results/trainable`.
        .. code-block:: python
            experiment_1 = tune.run(
                cost,
                num_samples=5,
                search_alg=search_alg,
                verbose=0,
                name=self.experiment_name,
                local_dir="~/my_results")
            search_alg2 = Searcher()
            search_alg2.restore_from_dir(
                os.path.join("~/my_results", self.experiment_name)
        """

        pattern = self.CKPT_FILE_TMPL.format("*")
        full_paths = glob.glob(os.path.join(checkpoint_dir, pattern))
        if not full_paths:
            raise RuntimeError(
                "Searcher unable to find checkpoint in {}".format(
                    checkpoint_dir))  # TODO
        most_recent_checkpoint = max(full_paths)
        self.restore(most_recent_checkpoint)

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
    .. code-block:: python
        from ray.tune.suggest import ConcurrencyLimiter
        search_alg = HyperOptSearch(metric="accuracy")
        search_alg = ConcurrencyLimiter(search_alg, max_concurrent=2)
        tune.run(trainable, search_alg=search_alg)
    """

    def __init__(self,
                 searcher: Searcher,
                 max_concurrent: int,
                 batch: bool = False):
        assert type(max_concurrent) is int and max_concurrent > 0
        self.searcher = searcher
        self.max_concurrent = max_concurrent
        self.batch = batch
        self.live_trials = set()
        self.cached_results = {}
        super(ConcurrencyLimiter, self).__init__(
            metric=self.searcher.metric, mode=self.searcher.mode)

    def suggest(self, trial_id: str) -> Optional[Dict]:
        assert trial_id not in self.live_trials, (
            f"Trial ID {trial_id} must be unique: already found in set.")
        if len(self.live_trials) >= self.max_concurrent:
            logger.debug(
                f"Not providing a suggestion for {trial_id} due to "
                "concurrency limit: %s/%s.", len(self.live_trials),
                self.max_concurrent)
            return

        suggestion = self.searcher.suggest(trial_id)
        if suggestion not in (None, Searcher.FINISHED):
            self.live_trials.add(trial_id)
        return suggestion

    def on_trial_complete(self,
                          trial_id: str,
                          result: Optional[Dict] = None,
                          error: bool = False):
        if trial_id not in self.live_trials:
            return
        elif self.batch:
            self.cached_results[trial_id] = (result, error)
            if len(self.cached_results) == self.max_concurrent:
                # Update the underlying searcher once the
                # full batch is completed.
                for trial_id, (result, error) in self.cached_results.items():
                    self.searcher.on_trial_complete(
                        trial_id, result=result, error=error)
                    self.live_trials.remove(trial_id)
                self.cached_results = {}
            else:
                return
        else:
            self.searcher.on_trial_complete(
                trial_id, result=result, error=error)
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

    def set_search_properties(self, metric: Optional[str], mode: Optional[str],
                              config: Dict) -> bool:
        return self.searcher.set_search_properties(metric, mode, config)


try:
    import optuna as ot
    from optuna.samplers import BaseSampler
except ImportError:
    ot = None
    BaseSampler = None


class _Param:
    def __getattr__(self, item):
        def _inner(*args, **kwargs):
            return (item, args, kwargs)

        return _inner


param = _Param()


# (Optional) Default (anonymous) metric when using tune.report(x)
DEFAULT_METRIC = "_metric"

# (Auto-filled) The index of this training iteration.
TRAINING_ITERATION = "training_iteration"


class OptunaSearch(Searcher):
    """A wrapper around Optuna to provide trial suggestions.
    `Optuna <https://optuna.org/>`_ is a hyperparameter optimization library.
    In contrast to other libraries, it employs define-by-run style
    hyperparameter definitions.
    This Searcher is a thin wrapper around Optuna's search algorithms.
    You can pass any Optuna sampler, which will be used to generate
    hyperparameter suggestions.
    Please note that this wrapper does not support define-by-run, so the
    search space will be configured before running the optimization. You will
    also need to use a Tune trainable (e.g. using the function API) with
    this wrapper.
    For defining the search space, use ``ray.tune.suggest.optuna.param``
    (see example).
    Args:
        space (list): Hyperparameter search space definition for Optuna's
            sampler. This is a list, and samples for the parameters will
            be obtained in order.
        metric (str): The training result objective value attribute. If None
            but a mode was passed, the anonymous metric `_metric` will be used
            per default.
        mode (str): One of {min, max}. Determines whether objective is
            minimizing or maximizing the metric attribute.
        points_to_evaluate (list): Initial parameter suggestions to be run
            first. This is for when you already have some good parameters
            you want to run first to help the algorithm make better suggestions
            for future parameters. Needs to be a list of dicts containing the
            configurations.
        sampler (optuna.samplers.BaseSampler): Optuna sampler used to
            draw hyperparameter configurations. Defaults to ``TPESampler``.
    Tune automatically converts search spaces to Optuna's format:
    .. code-block:: python
        from ray.tune.suggest.optuna import OptunaSearch
        config = {
            "a": tune.uniform(6, 8)
            "b": tune.uniform(10, 20)
        }
        optuna_search = OptunaSearch(
            metric="loss",
            mode="min")
        tune.run(trainable, config=config, search_alg=optuna_search)
    If you would like to pass the search space manually, the code would
    look like this:
    .. code-block:: python
        from ray.tune.suggest.optuna import OptunaSearch, param
        space = [
            param.suggest_uniform("a", 6, 8),
            param.suggest_uniform("b", 10, 20)
        ]
        algo = OptunaSearch(
            space,
            metric="loss",
            mode="min")
        tune.run(trainable, search_alg=optuna_search)
    .. versionadded:: 0.8.8
    """

    def __init__(self,
                 space: Optional[Union[Dict, List[Tuple]]] = None,
                 metric: Optional[str] = None,
                 mode: Optional[str] = None,
                 points_to_evaluate: Optional[List[Dict]] = None,
                 sampler: Optional[BaseSampler] = None):
        assert ot is not None, (
            "Optuna must be installed! Run `pip install optuna`.")
        super(OptunaSearch, self).__init__(
            metric=metric,
            mode=mode,
            max_concurrent=None,
            use_early_stopped_trials=None)

        if isinstance(space, dict) and space:
            resolved_vars, domain_vars, grid_vars = parse_spec_vars(space)
            if domain_vars or grid_vars:
                logger.warning(
                    UNRESOLVED_SEARCH_SPACE.format(
                        par="space", cls=type(self)))
                space = self.convert_search_space(space)

        self._space = space

        self._points_to_evaluate = points_to_evaluate

        self._study_name = "optuna"  # Fixed study name for in-memory storage
        self._sampler = sampler or ot.samplers.TPESampler()
        assert isinstance(self._sampler, BaseSampler), \
            "You can only pass an instance of `optuna.samplers.BaseSampler` " \
            "as a sampler to `OptunaSearcher`."

        self._pruner = ot.pruners.NopPruner()
        self._storage = ot.storages.InMemoryStorage()

        self._ot_trials = {}
        self._ot_study = None
        if self._space:
            self._setup_study(mode)

    def _setup_study(self, mode: str):
        if self._metric is None and self._mode:
            # If only a mode was passed, use anonymous metric
            self._metric = DEFAULT_METRIC

        self._ot_study = ot.study.create_study(
            storage=self._storage,
            sampler=self._sampler,
            pruner=self._pruner,
            study_name=self._study_name,
            direction="minimize" if mode == "min" else "maximize",
            load_if_exists=True)

    def set_search_properties(self, metric: Optional[str], mode: Optional[str],
                              config: Dict) -> bool:
        if self._space:
            return False
        space = self.convert_search_space(config)
        self._space = space
        if metric:
            self._metric = metric
        if mode:
            self._mode = mode

        self._setup_study(mode)
        return True

    def suggest(self, trial_id: str) -> Optional[Dict]:
        if not self._space:
            raise RuntimeError(
                UNDEFINED_SEARCH_SPACE.format(
                    cls=self.__class__.__name__, space="space"))
        if not self._metric or not self._mode:
            raise RuntimeError(
                UNDEFINED_METRIC_MODE.format(
                    cls=self.__class__.__name__,
                    metric=self._metric,
                    mode=self._mode))

        if trial_id not in self._ot_trials:
            ot_trial_id = self._storage.create_new_trial(
                self._ot_study._study_id)
            self._ot_trials[trial_id] = ot.trial.Trial(self._ot_study,
                                                       ot_trial_id)
        ot_trial = self._ot_trials[trial_id]

        if self._points_to_evaluate:
            params = self._points_to_evaluate.pop(0)
        else:
            # getattr will fetch the trial.suggest_ function on Optuna trials
            params = {
                args[0] if len(args) > 0 else kwargs["name"]: getattr(
                    ot_trial, fn)(*args, **kwargs)
                for (fn, args, kwargs) in self._space
            }
        return unflatten_dict(params)

    def on_trial_result(self, trial_id: str, result: Dict):
        metric = result[self.metric]
        step = result[TRAINING_ITERATION]
        ot_trial = self._ot_trials[trial_id]
        ot_trial.report(metric, step)

    def on_trial_complete(self,
                          trial_id: str,
                          result: Optional[Dict] = None,
                          error: bool = False):
        ot_trial = self._ot_trials[trial_id]
        ot_trial_id = ot_trial._trial_id
        self._storage.set_trial_value(ot_trial_id, result.get(
            self.metric, None))
        self._storage.set_trial_state(ot_trial_id,
                                      ot.trial.TrialState.COMPLETE)

    def save(self, checkpoint_path: str):
        save_object = (self._storage, self._pruner, self._sampler,
                       self._ot_trials, self._ot_study,
                       self._points_to_evaluate)
        with open(checkpoint_path, "wb") as outputFile:
            pickle.dump(save_object, outputFile)

    def restore(self, checkpoint_path: str):
        with open(checkpoint_path, "rb") as inputFile:
            save_object = pickle.load(inputFile)
        self._storage, self._pruner, self._sampler, \
            self._ot_trials, self._ot_study, \
            self._points_to_evaluate = save_object

    @staticmethod
    def convert_search_space(spec: Dict) -> List[Tuple]:
        resolved_vars, domain_vars, grid_vars = parse_spec_vars(spec)

        if not domain_vars and not grid_vars:
            return []

        if grid_vars:
            raise ValueError(
                "Grid search parameters cannot be automatically converted "
                "to an Optuna search space.")

        # Flatten and resolve again after checking for grid search.
        spec = flatten_dict(spec, prevent_delimiter=True)
        resolved_vars, domain_vars, grid_vars = parse_spec_vars(spec)

        def resolve_value(par: str, domain: Domain) -> Tuple:
            quantize = None

            sampler = domain.get_sampler()
            if isinstance(sampler, Quantized):
                quantize = sampler.q
                sampler = sampler.sampler

            if isinstance(domain, Float):
                if isinstance(sampler, LogUniform):
                    if quantize:
                        logger.warning(
                            "Optuna does not support both quantization and "
                            "sampling from LogUniform. Dropped quantization.")
                    return param.suggest_loguniform(par, domain.lower,
                                                    domain.upper)
                elif isinstance(sampler, Uniform):
                    if quantize:
                        return param.suggest_discrete_uniform(
                            par, domain.lower, domain.upper, quantize)
                    return param.suggest_uniform(par, domain.lower,
                                                 domain.upper)
            elif isinstance(domain, Integer):
                if isinstance(sampler, LogUniform):
                    if quantize:
                        logger.warning(
                            "Optuna does not support both quantization and "
                            "sampling from LogUniform. Dropped quantization.")
                    return param.suggest_int(
                        par, domain.lower, domain.upper, log=True)
                elif isinstance(sampler, Uniform):
                    return param.suggest_int(
                        par, domain.lower, domain.upper, step=quantize or 1)
            elif isinstance(domain, Categorical):
                if isinstance(sampler, Uniform):
                    return param.suggest_categorical(par, domain.categories)

            raise ValueError(
                "Optuna search does not support parameters of type "
                "`{}` with samplers of type `{}`".format(
                    type(domain).__name__,
                    type(domain.sampler).__name__))

        # Parameter name is e.g. "a/b/c" for nested dicts
        values = [
            resolve_value("/".join(path), domain)
            for path, domain in domain_vars
        ]

        return values
