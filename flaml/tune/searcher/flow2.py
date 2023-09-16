# !
#  * Copyright (c) Microsoft Corporation. All rights reserved.
#  * Licensed under the MIT License. See LICENSE file in the
#  * project root for license information.
from typing import Dict, Optional, Tuple
import numpy as np
import logging
from collections import defaultdict

try:
    from ray import __version__ as ray_version

    assert ray_version >= "1.0.0"
    if ray_version.startswith("1."):
        from ray.tune.suggest import Searcher
        from ray.tune import sample
    else:
        from ray.tune.search import Searcher, sample
    from ray.tune.utils.util import flatten_dict, unflatten_dict
except (ImportError, AssertionError):
    from .suggestion import Searcher
    from flaml.tune import sample
    from ..trial import flatten_dict, unflatten_dict
from flaml.config import SAMPLE_MULTIPLY_FACTOR
from ..space import (
    complete_config,
    denormalize,
    normalize,
    generate_variants_compatible,
)

logger = logging.getLogger(__name__)


class FLOW2(Searcher):
    """Local search algorithm FLOW2, with adaptive step size."""

    STEPSIZE = 0.1
    STEP_LOWER_BOUND = 0.0001

    def __init__(
        self,
        init_config: dict,
        metric: Optional[str] = None,
        mode: Optional[str] = None,
        space: Optional[dict] = None,
        resource_attr: Optional[str] = None,
        min_resource: Optional[float] = None,
        max_resource: Optional[float] = None,
        resource_multiple_factor: Optional[float] = None,
        cost_attr: Optional[str] = "time_total_s",
        seed: Optional[int] = 20,
        lexico_objectives=None,
    ):
        """Constructor.

        Args:
            init_config: a dictionary of a partial or full initial config,
                e.g., from a subset of controlled dimensions
                to the initial low-cost values.
                E.g., {'epochs': 1}.
            metric: A string of the metric name to optimize for.
            mode: A string in ['min', 'max'] to specify the objective as
                minimization or maximization.
            space: A dictionary to specify the search space.
            resource_attr: A string to specify the resource dimension and the best
                performance is assumed to be at the max_resource.
            min_resource: A float of the minimal resource to use for the resource_attr.
            max_resource: A float of the maximal resource to use for the resource_attr.
            resource_multiple_factor: A float of the multiplicative factor
                used for increasing resource.
            cost_attr: A string of the attribute used for cost.
            seed: An integer of the random seed.
            lexico_objectives: dict, default=None | It specifics information needed to perform multi-objective
                optimization with lexicographic preferences. When lexico_objectives is not None, the arguments metric,
                mode will be invalid. This dictionary shall contain the following fields of key-value pairs:
                - "metrics":  a list of optimization objectives with the orders reflecting the priorities/preferences of the
                objectives.
                - "modes" (optional): a list of optimization modes (each mode either "min" or "max") corresponding to the
                objectives in the metric list. If not provided, we use "min" as the default mode for all the objectives
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
        """
        if mode:
            assert mode in ["min", "max"], "`mode` must be 'min' or 'max'."
        else:
            mode = "min"

        super(FLOW2, self).__init__(metric=metric, mode=mode)
        # internally minimizes, so "max" => -1
        if mode == "max":
            self.metric_op = -1.0
        elif mode == "min":
            self.metric_op = 1.0
        self.space = space or {}
        self._space = flatten_dict(self.space, prevent_delimiter=True)
        self._random = np.random.RandomState(seed)
        self.rs_random = sample._BackwardsCompatibleNumpyRng(seed + 19823)
        self.seed = seed
        self.init_config = init_config
        self.best_config = flatten_dict(init_config)
        self.resource_attr = resource_attr
        self.min_resource = min_resource
        self.lexico_objectives = lexico_objectives
        if self.lexico_objectives is not None:
            if "modes" not in self.lexico_objectives.keys():
                self.lexico_objectives["modes"] = ["min"] * len(self.lexico_objectives["metrics"])
            for t_metric, t_mode in zip(self.lexico_objectives["metrics"], self.lexico_objectives["modes"]):
                if t_metric not in self.lexico_objectives["tolerances"].keys():
                    self.lexico_objectives["tolerances"][t_metric] = 0
                if t_metric not in self.lexico_objectives["targets"].keys():
                    self.lexico_objectives["targets"][t_metric] = -float("inf") if t_mode == "min" else float("inf")
        self.resource_multiple_factor = resource_multiple_factor or SAMPLE_MULTIPLY_FACTOR
        self.cost_attr = cost_attr
        self.max_resource = max_resource
        self._resource = None
        self._f_best = None  # only use for lexico_comapre. It represent the best value achieved by lexico_flow.
        self._step_lb = np.Inf
        self._histories = None  # only use for lexico_comapre. It records the result of historical configurations.
        if space is not None:
            self._init_search()

    def _init_search(self):
        self._tunable_keys = []
        self._bounded_keys = []
        self._unordered_cat_hp = {}
        hier = False
        for key, domain in self._space.items():
            assert not (
                isinstance(domain, dict) and "grid_search" in domain
            ), f"{key}'s domain is grid search, not supported in FLOW^2."
            if callable(getattr(domain, "get_sampler", None)):
                self._tunable_keys.append(key)
                sampler = domain.get_sampler()
                # the step size lower bound for uniform variables doesn't depend
                # on the current config
                if isinstance(sampler, sample.Quantized):
                    q = sampler.q
                    sampler = sampler.get_sampler()
                    if str(sampler) == "Uniform":
                        self._step_lb = min(self._step_lb, q / (domain.upper - domain.lower + 1))
                elif isinstance(domain, sample.Integer) and str(sampler) == "Uniform":
                    self._step_lb = min(self._step_lb, 1.0 / (domain.upper - domain.lower))
                if isinstance(domain, sample.Categorical):
                    if not domain.ordered:
                        self._unordered_cat_hp[key] = len(domain.categories)
                    if not hier:
                        for cat in domain.categories:
                            if isinstance(cat, dict):
                                hier = True
                                break
                if str(sampler) != "Normal":
                    self._bounded_keys.append(key)
        if not hier:
            self._space_keys = sorted(self._tunable_keys)
        self.hierarchical = hier
        if self.resource_attr and self.resource_attr not in self._space and self.max_resource:
            self.min_resource = self.min_resource or self._min_resource()
            self._resource = self._round(self.min_resource)
            if not hier:
                self._space_keys.append(self.resource_attr)
        else:
            self._resource = None
        self.incumbent = {}
        self.incumbent = self.normalize(self.best_config)  # flattened
        self.best_obj = self.cost_incumbent = None
        self.dim = len(self._tunable_keys)  # total # tunable dimensions
        self._direction_tried = None
        self._num_complete4incumbent = self._cost_complete4incumbent = 0
        self._num_allowed4incumbent = 2 * self.dim
        self._proposed_by = {}  # trial_id: int -> incumbent: Dict
        self.step_ub = np.sqrt(self.dim)
        self.step = self.STEPSIZE * self.step_ub
        lb = self.step_lower_bound
        if lb > self.step:
            self.step = lb * 2
        # upper bound
        self.step = min(self.step, self.step_ub)
        # maximal # consecutive no improvements
        self.dir = 2 ** (min(9, self.dim))
        self._configs = {}  # dict from trial_id to (config, stepsize)
        self._K = 0
        self._iter_best_config = 1
        self.trial_count_proposed = self.trial_count_complete = 1
        self._num_proposedby_incumbent = 0
        self._reset_times = 0
        # record intermediate trial cost
        self._trial_cost = {}
        self._same = False  # whether the proposed config is the same as best_config
        self._init_phase = True  # initial phase to increase initial stepsize
        self._trunc = 0
        # no truncation by default. when > 0, it means how many
        # non-zero dimensions to keep in the random unit vector

    @property
    def step_lower_bound(self) -> float:
        step_lb = self._step_lb
        for key in self._tunable_keys:
            if key not in self.best_config:
                continue
            domain = self._space[key]
            sampler = domain.get_sampler()
            # the stepsize lower bound for log uniform variables depends on the
            # current config
            if isinstance(sampler, sample.Quantized):
                q = sampler.q
                sampler_inner = sampler.get_sampler()
                if str(sampler_inner) == "LogUniform":
                    step_lb = min(
                        step_lb,
                        np.log(1.0 + q / self.best_config[key]) / np.log(domain.upper / domain.lower),
                    )
            elif isinstance(domain, sample.Integer) and str(sampler) == "LogUniform":
                step_lb = min(
                    step_lb,
                    np.log(1.0 + 1.0 / self.best_config[key]) / np.log((domain.upper - 1) / domain.lower),
                )
        if np.isinf(step_lb):
            step_lb = self.STEP_LOWER_BOUND
        else:
            step_lb *= self.step_ub
        return step_lb

    @property
    def resource(self) -> float:
        return self._resource

    def _min_resource(self) -> float:
        """automatically decide minimal resource"""
        return self.max_resource / np.pow(self.resource_multiple_factor, 5)

    def _round(self, resource) -> float:
        """round the resource to self.max_resource if close to it"""
        if resource * self.resource_multiple_factor > self.max_resource:
            return self.max_resource
        return resource

    def rand_vector_gaussian(self, dim, std=1.0):
        return self._random.normal(0, std, dim)

    def complete_config(
        self,
        partial_config: Dict,
        lower: Optional[Dict] = None,
        upper: Optional[Dict] = None,
    ) -> Tuple[Dict, Dict]:
        """Generate a complete config from the partial config input.

        Add minimal resource to config if available.
        """
        disturb = self._reset_times and partial_config == self.init_config
        # if not the first time to complete init_config, use random gaussian
        config, space = complete_config(partial_config, self.space, self, disturb, lower, upper)
        if partial_config == self.init_config:
            self._reset_times += 1
        if self._resource:
            config[self.resource_attr] = self.min_resource
        return config, space

    def create(self, init_config: Dict, obj: float, cost: float, space: Dict) -> Searcher:
        # space is the subspace where the init_config is located
        flow2 = self.__class__(
            init_config,
            self.metric,
            self.mode,
            space,
            self.resource_attr,
            self.min_resource,
            self.max_resource,
            self.resource_multiple_factor,
            self.cost_attr,
            self.seed + 1,
            self.lexico_objectives,
        )
        if self.lexico_objectives is not None:
            flow2.best_obj = {}
            for k, v in obj.items():
                flow2.best_obj[k] = (
                    -v if self.lexico_objectives["modes"][self.lexico_objectives["metrics"].index(k)] == "max" else v
                )
        else:
            flow2.best_obj = obj * self.metric_op  # minimize internally
        flow2.cost_incumbent = cost
        self.seed += 1
        return flow2

    def normalize(self, config, recursive=False) -> Dict:
        """normalize each dimension in config to [0,1]."""
        return normalize(config, self._space, self.best_config, self.incumbent, recursive)

    def denormalize(self, config):
        """denormalize each dimension in config from [0,1]."""
        return denormalize(config, self._space, self.best_config, self.incumbent, self._random)

    def set_search_properties(
        self,
        metric: Optional[str] = None,
        mode: Optional[str] = None,
        config: Optional[Dict] = None,
    ) -> bool:
        if metric:
            self._metric = metric
        if mode:
            assert mode in ["min", "max"], "`mode` must be 'min' or 'max'."
            self._mode = mode
            if mode == "max":
                self.metric_op = -1.0
            elif mode == "min":
                self.metric_op = 1.0
        if config:
            self.space = config
            self._space = flatten_dict(self.space)
            self._init_search()
        return True

    def update_fbest(
        self,
    ):
        obj_initial = self.lexico_objectives["metrics"][0]
        feasible_index = np.array([*range(len(self._histories[obj_initial]))])
        for k_metric in self.lexico_objectives["metrics"]:
            k_values = np.array(self._histories[k_metric])
            feasible_value = k_values.take(feasible_index)
            self._f_best[k_metric] = np.min(feasible_value)
            if not isinstance(self.lexico_objectives["tolerances"][k_metric], str):
                tolerance_bound = self._f_best[k_metric] + self.lexico_objectives["tolerances"][k_metric]
            else:
                assert (
                    self.lexico_objectives["tolerances"][k_metric][-1] == "%"
                ), "String tolerance of {} should use %% as the suffix".format(k_metric)
                tolerance_bound = self._f_best[k_metric] * (
                    1 + 0.01 * float(self.lexico_objectives["tolerances"][k_metric].replace("%", ""))
                )
            feasible_index_filter = np.where(
                feasible_value
                <= max(
                    tolerance_bound,
                    self.lexico_objectives["targets"][k_metric],
                )
            )[0]
            feasible_index = feasible_index.take(feasible_index_filter)

    def lexico_compare(self, result) -> bool:
        if self._histories is None:
            self._histories, self._f_best = defaultdict(list), {}
            for k in self.lexico_objectives["metrics"]:
                self._histories[k].append(result[k])
            self.update_fbest()
            return True
        else:
            for k in self.lexico_objectives["metrics"]:
                self._histories[k].append(result[k])
            self.update_fbest()
            for k_metric, k_mode in zip(self.lexico_objectives["metrics"], self.lexico_objectives["modes"]):
                k_target = (
                    self.lexico_objectives["targets"][k_metric]
                    if k_mode == "min"
                    else -self.lexico_objectives["targets"][k_metric]
                )
                if not isinstance(self.lexico_objectives["tolerances"][k_metric], str):
                    tolerance_bound = self._f_best[k_metric] + self.lexico_objectives["tolerances"][k_metric]
                else:
                    assert (
                        self.lexico_objectives["tolerances"][k_metric][-1] == "%"
                    ), "String tolerance of {} should use %% as the suffix".format(k_metric)
                    tolerance_bound = self._f_best[k_metric] * (
                        1 + 0.01 * float(self.lexico_objectives["tolerances"][k_metric].replace("%", ""))
                    )
                if (result[k_metric] < max(tolerance_bound, k_target)) and (
                    self.best_obj[k_metric]
                    < max(
                        tolerance_bound,
                        k_target,
                    )
                ):
                    continue
                elif result[k_metric] < self.best_obj[k_metric]:
                    return True
                else:
                    return False
            for k_metr in self.lexico_objectives["metrics"]:
                if result[k_metr] == self.best_obj[k_metr]:
                    continue
                elif result[k_metr] < self.best_obj[k_metr]:
                    return True
                else:
                    return False

    def on_trial_complete(self, trial_id: str, result: Optional[Dict] = None, error: bool = False):
        """
        Compare with incumbent.
        If better, move, reset num_complete and num_proposed.
        If not better and num_complete >= 2*dim, num_allowed += 2.
        """
        self.trial_count_complete += 1
        if not error and result:
            obj = (
                result.get(self._metric)
                if self.lexico_objectives is None
                else {k: result[k] for k in self.lexico_objectives["metrics"]}
            )
            if obj:
                obj = (
                    {
                        k: -obj[k] if m == "max" else obj[k]
                        for k, m in zip(
                            self.lexico_objectives["metrics"],
                            self.lexico_objectives["modes"],
                        )
                    }
                    if isinstance(obj, dict)
                    else obj * self.metric_op
                )
                if (
                    self.best_obj is None
                    or (self.lexico_objectives is None and obj < self.best_obj)
                    or (self.lexico_objectives is not None and self.lexico_compare(obj))
                ):
                    self.best_obj = obj
                    self.best_config, self.step = self._configs[trial_id]
                    self.incumbent = self.normalize(self.best_config)
                    self.cost_incumbent = result.get(self.cost_attr, 1)
                    if self._resource:
                        self._resource = self.best_config[self.resource_attr]
                    self._num_complete4incumbent = 0
                    self._cost_complete4incumbent = 0
                    self._num_proposedby_incumbent = 0
                    self._num_allowed4incumbent = 2 * self.dim
                    self._proposed_by.clear()
                    if self._K > 0:
                        self.step *= np.sqrt(self._K / self._oldK)
                    self.step = min(self.step, self.step_ub)
                    self._iter_best_config = self.trial_count_complete
                    if self._trunc:
                        self._trunc = min(self._trunc + 1, self.dim)
                    return
                elif self._trunc:
                    self._trunc = max(self._trunc >> 1, 1)
        proposed_by = self._proposed_by.get(trial_id)
        if proposed_by == self.incumbent:
            self._num_complete4incumbent += 1
            cost = result.get(self.cost_attr, 1) if result else self._trial_cost.get(trial_id)
            if cost:
                self._cost_complete4incumbent += cost
            if self._num_complete4incumbent >= 2 * self.dim and self._num_allowed4incumbent == 0:
                self._num_allowed4incumbent = 2
            if self._num_complete4incumbent == self.dir and (not self._resource or self._resource == self.max_resource):
                self._num_complete4incumbent -= 2
                self._num_allowed4incumbent = max(self._num_allowed4incumbent, 2)

    def on_trial_result(self, trial_id: str, result: Dict):
        """Early update of incumbent."""
        if result:
            obj = (
                result.get(self._metric)
                if self.lexico_objectives is None
                else {k: result[k] for k in self.lexico_objectives["metrics"]}
            )
            if obj:
                obj = (
                    {
                        k: -obj[k] if m == "max" else obj[k]
                        for k, m in zip(
                            self.lexico_objectives["metrics"],
                            self.lexico_objectives["modes"],
                        )
                    }
                    if isinstance(obj, dict)
                    else obj * self.metric_op
                )
                if (
                    self.best_obj is None
                    or (self.lexico_objectives is None and obj < self.best_obj)
                    or (self.lexico_objectives is not None and self.lexico_compare(obj))
                ):
                    self.best_obj = obj
                    config = self._configs[trial_id][0]
                    if self.best_config != config:
                        self.best_config = config
                        if self._resource:
                            self._resource = config[self.resource_attr]
                        self.incumbent = self.normalize(self.best_config)
                        self.cost_incumbent = result.get(self.cost_attr, 1)
                        self._cost_complete4incumbent = 0
                        self._num_complete4incumbent = 0
                        self._num_proposedby_incumbent = 0
                        self._num_allowed4incumbent = 2 * self.dim
                        self._proposed_by.clear()
                        self._iter_best_config = self.trial_count_complete
            cost = result.get(self.cost_attr, 1)
            # record the cost in case it is pruned and cost info is lost
            self._trial_cost[trial_id] = cost

    def rand_vector_unit_sphere(self, dim, trunc=0) -> np.ndarray:
        vec = self._random.normal(0, 1, dim)
        if 0 < trunc < dim:
            vec[np.abs(vec).argsort()[: dim - trunc]] = 0
        mag = np.linalg.norm(vec)
        return vec / mag

    def suggest(self, trial_id: str) -> Optional[Dict]:
        """Suggest a new config, one of the following cases:
        1. same incumbent, increase resource.
        2. same resource, move from the incumbent to a random direction.
        3. same resource, move from the incumbent to the opposite direction.
        """
        # TODO: better decouple FLOW2 config suggestion and stepsize update
        self.trial_count_proposed += 1
        if (
            self._num_complete4incumbent > 0
            and self.cost_incumbent
            and self._resource
            and self._resource < self.max_resource
            and (self._cost_complete4incumbent >= self.cost_incumbent * self.resource_multiple_factor)
        ):
            return self._increase_resource(trial_id)
        self._num_allowed4incumbent -= 1
        move = self.incumbent.copy()
        if self._direction_tried is not None:
            # return negative direction
            for i, key in enumerate(self._tunable_keys):
                move[key] -= self._direction_tried[i]
            self._direction_tried = None
        else:
            # propose a new direction
            self._direction_tried = self.rand_vector_unit_sphere(self.dim, self._trunc) * self.step
            for i, key in enumerate(self._tunable_keys):
                move[key] += self._direction_tried[i]
        self._project(move)
        config = self.denormalize(move)
        self._proposed_by[trial_id] = self.incumbent
        self._configs[trial_id] = (config, self.step)
        self._num_proposedby_incumbent += 1
        best_config = self.best_config
        if self._init_phase:
            if self._direction_tried is None:
                if self._same:
                    same = not any(key not in best_config or value != best_config[key] for key, value in config.items())

                    if same:
                        # increase step size
                        self.step += self.STEPSIZE
                        self.step = min(self.step, self.step_ub)
            else:
                same = not any(key not in best_config or value != best_config[key] for key, value in config.items())

                self._same = same
        if self._num_proposedby_incumbent == self.dir and (not self._resource or self._resource == self.max_resource):
            # check stuck condition if using max resource
            self._num_proposedby_incumbent -= 2
            self._init_phase = False
            if self.step < self.step_lower_bound:
                return None
                # decrease step size
            self._oldK = self._K or self._iter_best_config
            self._K = self.trial_count_proposed + 1
            self.step *= np.sqrt(self._oldK / self._K)
        if self._init_phase:
            return unflatten_dict(config)
        if self._trunc == 1 and self._direction_tried is not None:
            # random
            for i, key in enumerate(self._tunable_keys):
                if self._direction_tried[i] != 0:
                    for _, generated in generate_variants_compatible(
                        {"config": {key: self._space[key]}}, random_state=self.rs_random
                    ):
                        if generated["config"][key] != best_config[key]:
                            config[key] = generated["config"][key]
                            return unflatten_dict(config)
                        break
        elif len(config) == len(best_config):
            for key, value in best_config.items():
                if value != config[key]:
                    return unflatten_dict(config)
            # print('move to', move)
            self.incumbent = move
        return unflatten_dict(config)

    def _increase_resource(self, trial_id):
        # consider increasing resource using sum eval cost of complete
        # configs
        old_resource = self._resource
        self._resource = self._round(self._resource * self.resource_multiple_factor)
        self.cost_incumbent *= self._resource / old_resource
        config = self.best_config.copy()
        config[self.resource_attr] = self._resource
        self._direction_tried = None
        self._configs[trial_id] = (config, self.step)
        return unflatten_dict(config)

    def _project(self, config):
        """project normalized config in the feasible region and set resource_attr"""
        for key in self._bounded_keys:
            value = config[key]
            config[key] = max(0, min(1, value))
        if self._resource:
            config[self.resource_attr] = self._resource

    @property
    def can_suggest(self) -> bool:
        """Can't suggest if 2*dim configs have been proposed for the incumbent
        while fewer are completed.
        """
        return self._num_allowed4incumbent > 0

    def config_signature(self, config, space: Dict = None) -> tuple:
        """Return the signature tuple of a config."""
        config = flatten_dict(config)
        space = flatten_dict(space) if space else self._space
        value_list = []
        # self._space_keys doesn't contain keys with const values,
        # e.g., "eval_metric": ["logloss", "error"].
        keys = sorted(config.keys()) if self.hierarchical else self._space_keys
        for key in keys:
            value = config[key]
            if key == self.resource_attr:
                value_list.append(value)
            else:
                # key must be in space
                domain = space[key]
                if self.hierarchical and not (
                    domain is None or type(domain) in (str, int, float) or isinstance(domain, sample.Domain)
                ):
                    # not domain or hashable
                    # get rid of list type for hierarchical search space.
                    continue
                if isinstance(domain, sample.Integer):
                    value_list.append(int(round(value)))
                else:
                    value_list.append(value)
        return tuple(value_list)

    @property
    def converged(self) -> bool:
        """Whether the local search has converged."""
        if self._num_complete4incumbent < self.dir - 2:
            return False
        # check stepsize after enough configs are completed
        return self.step < self.step_lower_bound

    def reach(self, other: Searcher) -> bool:
        """whether the incumbent can reach the incumbent of other."""
        config1, config2 = self.best_config, other.best_config
        incumbent1, incumbent2 = self.incumbent, other.incumbent
        if self._resource and config1[self.resource_attr] > config2[self.resource_attr]:
            # resource will not decrease
            return False
        for key in self._unordered_cat_hp:
            # unordered cat choice is hard to reach by chance
            if config1[key] != config2.get(key):
                return False
        delta = np.array([incumbent1[key] - incumbent2.get(key, np.inf) for key in self._tunable_keys])
        return np.linalg.norm(delta) <= self.step
