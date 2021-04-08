'''!
 * Copyright (c) 2020-2021 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in the
 * project root for license information.
'''
from typing import Dict, Optional
import numpy as np
try:
    from ray.tune.suggest import Searcher
    from ray.tune.suggest.variant_generator import generate_variants
    from ray.tune import sample
    from ray.tune.utils.util import flatten_dict, unflatten_dict
except ImportError:
    from .suggestion import Searcher
    from .variant_generator import generate_variants, flatten_dict, unflatten_dict
    from ..tune import sample


import logging
logger = logging.getLogger(__name__)


class FLOW2(Searcher):
    '''Local search algorithm FLOW2, with adaptive step size
    '''

    STEPSIZE = 0.1
    STEP_LOWER_BOUND = 0.0001
    cost_attr = 'time_total_s'

    def __init__(self,
                 init_config: dict,
                 metric: Optional[str] = None,
                 mode: Optional[str] = None,
                 cat_hp_cost: Optional[dict] = None,
                 space: Optional[dict] = None,
                 prune_attr: Optional[str] = None,
                 min_resource: Optional[float] = None,
                 max_resource: Optional[float] = None,
                 resource_multiple_factor: Optional[float] = 4,
                 seed: Optional[int] = 20):
        '''Constructor

        Args:
            init_config: a dictionary of a partial or full initial config,
                e.g. from a subset of controlled dimensions
                to the initial low-cost values.
                e.g. {'epochs': 1}
            metric: A string of the metric name to optimize for.
                minimization or maximization.
            mode: A string in ['min', 'max'] to specify the objective as
            cat_hp_cost: A dictionary from a subset of categorical dimensions
                to the relative cost of each choice.
                e.g.,

                .. code-block:: python

                    {'tree_method': [1, 1, 2]}

                i.e., the relative cost of the
                three choices of 'tree_method' is 1, 1 and 2 respectively.
            space: A dictionary to specify the search space.
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
            resource_multiple_factor: A float of the multiplicative factor
                used for increasing resource.
            seed: An integer of the random seed.
        '''
        if mode:
            assert mode in ["min", "max"], "`mode` must be 'min' or 'max'."
        else:
            mode = "min"

        super(FLOW2, self).__init__(
            metric=metric,
            mode=mode)
        # internally minimizes, so "max" => -1
        if mode == "max":
            self.metric_op = -1.
        elif mode == "min":
            self.metric_op = 1.
        self.space = space or {}
        self.space = flatten_dict(self.space, prevent_delimiter=True)
        self._random = np.random.RandomState(seed)
        self._seed = seed
        if not init_config:
            logger.warning(
                "No init config given to FLOW2. Using random initial config."
                "For cost-frugal search, "
                "consider providing init values for cost-related hps via "
                "'init_config'."
            )
        self.init_config = init_config
        self.best_config = flatten_dict(init_config)
        self.cat_hp_cost = cat_hp_cost
        self.prune_attr = prune_attr
        self.min_resource = min_resource
        self.resource_multiple_factor = resource_multiple_factor or 4
        self.max_resource = max_resource
        self._resource = None
        self._step_lb = np.Inf
        if space:
            self._init_search()

    def _init_search(self):
        self._tunable_keys = []
        self._bounded_keys = []
        # choices of numeric values. integer encoding.
        # value: (ordered list of choices,
        #  dict from choice to index in the ordered list)
        self._ordered_choice_hp = {}
        # choices with given cost. integer encoding.
        # value: (array of choices ordered by cost,
        #  dict from choice to index in the ordered array)
        self._ordered_cat_hp = {}
        # unordered choices. value: cardinality
        self._unordered_cat_hp = {}
        self._cat_hp_cost = {}
        for key, domain in self.space.items():
            assert not (isinstance(domain, dict) and 'grid_search' in domain), \
                f"{key}'s domain is grid search, not supported in FLOW^2."
            if callable(getattr(domain, 'get_sampler', None)):
                self._tunable_keys.append(key)
                sampler = domain.get_sampler()
                # if isinstance(sampler, sample.Quantized):
                #     sampler_inner = sampler.get_sampler()
                #     if str(sampler_inner) == 'Uniform':
                #         self._step_lb = min(
                #             self._step_lb, sampler.q/(domain.upper-domain.lower))
                # elif isinstance(domain, sample.Integer) and str(
                #     sampler) == 'Uniform':
                #     self._step_lb = min(
                #         self._step_lb, 1.0/(domain.upper-domain.lower))
                if isinstance(domain, sample.Categorical):
                    cat_hp_cost = self.cat_hp_cost
                    if cat_hp_cost and key in cat_hp_cost:
                        cost = np.array(cat_hp_cost[key])
                        ind = np.argsort(cost)
                        ordered = np.array(domain.categories)[ind]
                        cost = self._cat_hp_cost[key] = cost[ind]
                        d = {}
                        for i, choice in enumerate(ordered):
                            d[choice] = i
                        self._ordered_cat_hp[key] = (ordered, d)
                    elif all(isinstance(x, int) or isinstance(x, float)
                             for x in domain.categories):
                        ordered = sorted(domain.categories)
                        d = {}
                        for i, choice in enumerate(ordered):
                            d[choice] = i
                        self._ordered_choice_hp[key] = (ordered, d)
                    else:
                        self._unordered_cat_hp[key] = len(domain.categories)
                if str(sampler) != 'Normal':
                    self._bounded_keys.append(key)
        self._space_keys = list(self.space.keys())
        if (self.prune_attr and self.prune_attr not in self.space
                and self.max_resource):
            self._space_keys.append(self.prune_attr)
            self.min_resource = self.min_resource or self._min_resource()
            self._resource = self._round(self.min_resource)
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
        self.step = self.STEPSIZE * np.sqrt(self.dim)
        lb = self.step_lower_bound
        if lb > self.step:
            self.step = lb * 2
        # upper bound
        self.step_ub = np.sqrt(self.dim)
        if self.step > self.step_ub:
            self.step = self.step_ub
        # maximal # consecutive no improvements
        self.dir = 2**(self.dim)
        self._configs = {}  # dict from trial_id to config
        self._K = 0
        self._iter_best_config = self.trial_count = 1
        self._reset_times = 0
        # record intermediate trial cost
        self._trial_cost = {}

    @property
    def step_lower_bound(self) -> float:
        step_lb = self._step_lb
        for key in self._tunable_keys:
            if key not in self.best_config:
                continue
            domain = self.space[key]
            sampler = domain.get_sampler()
            if isinstance(sampler, sample.Quantized):
                sampler_inner = sampler.get_sampler()
                if str(sampler_inner) == 'LogUniform':
                    step_lb = min(
                        step_lb, np.log(1.0 + sampler.q / self.best_config[key])
                        / np.log(domain.upper / domain.lower))
            elif isinstance(domain, sample.Integer) and str(sampler) == 'LogUniform':
                step_lb = min(
                    step_lb, np.log(1.0 + 1.0 / self.best_config[key])
                    / np.log(domain.upper / domain.lower))
        if np.isinf(step_lb):
            step_lb = self.STEP_LOWER_BOUND
        else:
            step_lb *= np.sqrt(self.dim)
        return step_lb

    @property
    def resource(self) -> float:
        return self._resource

    def _min_resource(self) -> float:
        ''' automatically decide minimal resource
        '''
        return self.max_resource / np.pow(self.resource_multiple_factor, 5)

    def _round(self, resource) -> float:
        ''' round the resource to self.max_resource if close to it
        '''
        if resource * self.resource_multiple_factor > self.max_resource:
            return self.max_resource
        return resource

    def rand_vector_gaussian(self, dim, std=1.0):
        vec = self._random.normal(0, std, dim)
        return vec

    def complete_config(
        self, partial_config: Dict,
        lower: Optional[Dict] = None, upper: Optional[Dict] = None
    ) -> Dict:
        ''' generate a complete config from the partial config input
        add minimal resource to config if available
        '''
        if self._reset_times and partial_config == self.init_config:
            # not the first time to complete init_config, use random gaussian
            normalized = self.normalize(partial_config)
            for key in normalized:
                # don't change unordered cat choice
                if key not in self._unordered_cat_hp:
                    if upper and lower:
                        up, low = upper[key], lower[key]
                        gauss_std = up - low or self.STEPSIZE
                        # allowed bound
                        up += self.STEPSIZE
                        low -= self.STEPSIZE
                    elif key in self._bounded_keys:
                        up, low, gauss_std = 1, 0, 1.0
                    else:
                        up, low, gauss_std = np.Inf, -np.Inf, 1.0
                    if key in self._bounded_keys:
                        up = min(up, 1)
                        low = max(low, 0)
                    delta = self.rand_vector_gaussian(1, gauss_std)[0]
                    normalized[key] = max(low, min(up, normalized[key] + delta))
            # use best config for unordered cat choice
            config = self.denormalize(normalized)
        else:
            # first time init_config, or other configs, take as is
            config = partial_config.copy()
        if partial_config == self.init_config:
            self._reset_times += 1
        config = flatten_dict(config)
        for key, value in self.space.items():
            if key not in config:
                config[key] = value
        for _, generated in generate_variants({'config': config}):
            config = generated['config']
            break
        if self._resource:
            config[self.prune_attr] = self.min_resource
        return unflatten_dict(config)

    def create(self, init_config: Dict, obj: float, cost: float) -> Searcher:
        flow2 = FLOW2(init_config, self.metric, self.mode, self._cat_hp_cost,
                      unflatten_dict(self.space), self.prune_attr,
                      self.min_resource, self.max_resource,
                      self.resource_multiple_factor, self._seed + 1)
        flow2.best_obj = obj * self.metric_op  # minimize internally
        flow2.cost_incumbent = cost
        return flow2

    def normalize(self, config) -> Dict:
        ''' normalize each dimension in config to [0,1]
        '''
        config_norm = {}
        for key, value in flatten_dict(config).items():
            if key in self.space:
                # domain: sample.Categorical/Integer/Float/Function
                domain = self.space[key]
                if not callable(getattr(domain, 'get_sampler', None)):
                    config_norm[key] = value
                else:
                    if isinstance(domain, sample.Categorical):
                        # normalize categorical
                        if key in self._ordered_cat_hp:
                            l, d = self._ordered_cat_hp[key]
                            config_norm[key] = (d[value] + 0.5) / len(l)
                        elif key in self._ordered_choice_hp:
                            l, d = self._ordered_choice_hp[key]
                            config_norm[key] = (d[value] + 0.5) / len(l)
                        elif key in self.incumbent:
                            config_norm[key] = self.incumbent[
                                key] if value == self.best_config[
                                    key] else (self.incumbent[
                                        key] + 1) % self._unordered_cat_hp[key]
                        else:
                            config_norm[key] = 0
                        continue
                    # Uniform/LogUniform/Normal/Base
                    sampler = domain.get_sampler()
                    if isinstance(sampler, sample.Quantized):
                        # sampler is sample.Quantized
                        sampler = sampler.get_sampler()
                    if str(sampler) == 'LogUniform':
                        config_norm[key] = np.log(value / domain.lower) / np.log(
                            domain.upper / domain.lower)
                    elif str(sampler) == 'Uniform':
                        config_norm[key] = (
                            value - domain.lower) / (domain.upper - domain.lower)
                    elif str(sampler) == 'Normal':
                        # N(mean, sd) -> N(0,1)
                        config_norm[key] = (value - sampler.mean) / sampler.sd
                    else:
                        # TODO? elif str(sampler) == 'Base': # sample.Function._CallSampler
                        # e.g., {test: sample_from(lambda spec: randn(10, 2).sample() * 0.01)}
                        config_norm[key] = value
            else:  # prune_attr
                config_norm[key] = value
        return config_norm

    def denormalize(self, config):
        ''' denormalize each dimension in config from [0,1]
        '''
        config_denorm = {}
        for key, value in config.items():
            if key in self.space:
                # domain: sample.Categorical/Integer/Float/Function
                domain = self.space[key]
                if not callable(getattr(domain, 'get_sampler', None)):
                    config_denorm[key] = value
                else:
                    if isinstance(domain, sample.Categorical):
                        # denormalize categorical
                        if key in self._ordered_cat_hp:
                            l, _ = self._ordered_cat_hp[key]
                            n = len(l)
                            config_denorm[key] = l[min(n - 1, int(np.floor(value * n)))]
                        elif key in self._ordered_choice_hp:
                            l, _ = self._ordered_choice_hp[key]
                            n = len(l)
                            config_denorm[key] = l[min(n - 1, int(np.floor(value * n)))]
                        else:
                            assert key in self.incumbent
                            if round(value) == self.incumbent[key]:
                                config_denorm[key] = self.best_config[key]
                            else:  # ****random value each time!****
                                config_denorm[key] = self._random.choice(
                                    [x for x in domain.categories
                                     if x != self.best_config[key]])
                        continue
                    # Uniform/LogUniform/Normal/Base
                    sampler = domain.get_sampler()
                    if isinstance(sampler, sample.Quantized):
                        # sampler is sample.Quantized
                        sampler = sampler.get_sampler()
                    # Handle Log/Uniform
                    if str(sampler) == 'LogUniform':
                        config_denorm[key] = (
                            domain.upper / domain.lower) ** value * domain.lower
                    elif str(sampler) == 'Uniform':
                        config_denorm[key] = value * (
                            domain.upper - domain.lower) + domain.lower
                    elif str(sampler) == 'Normal':
                        # denormalization for 'Normal'
                        config_denorm[key] = value * sampler.sd + sampler.mean
                    else:
                        config_denorm[key] = value
                    # Handle quantized
                    sampler = domain.get_sampler()
                    if isinstance(sampler, sample.Quantized):
                        config_denorm[key] = np.round(
                            np.divide(config_denorm[key], sampler.q)) * sampler.q
                    # Handle int (4.6 -> 5)
                    if isinstance(domain, sample.Integer):
                        config_denorm[key] = int(round(config_denorm[key]))
            else:  # prune_attr
                config_denorm[key] = value
        return config_denorm

    def set_search_properties(self,
                              metric: Optional[str] = None,
                              mode: Optional[str] = None,
                              config: Optional[Dict] = None) -> bool:
        if metric:
            self._metric = metric
        if mode:
            assert mode in ["min", "max"], "`mode` must be 'min' or 'max'."
            self._mode = mode
            if mode == "max":
                self.metric_op = -1.
            elif mode == "min":
                self.metric_op = 1.
        if config:
            self.space = config
            self._init_search()
        return True

    def on_trial_complete(self, trial_id: str, result: Optional[Dict] = None,
                          error: bool = False):
        ''' compare with incumbent
        '''
        # if better, move, reset num_complete and num_proposed
        # if not better and num_complete >= 2*dim, num_allowed += 2
        self.trial_count += 1
        if not error and result:
            obj = result.get(self._metric)
            if obj:
                obj *= self.metric_op
                if self.best_obj is None or obj < self.best_obj:
                    self.best_obj, self.best_config = obj, self._configs[
                        trial_id]
                    self.incumbent = self.normalize(self.best_config)
                    self.cost_incumbent = result.get(self.cost_attr)
                    if self._resource:
                        self._resource = self.best_config[self.prune_attr]
                    self._num_complete4incumbent = 0
                    self._cost_complete4incumbent = 0
                    self._num_allowed4incumbent = 2 * self.dim
                    self._proposed_by.clear()
                    if self._K > 0:
                        # self._oldK must have been set when self._K>0
                        self.step *= np.sqrt(self._K / self._oldK)
                    if self.step > self.step_ub:
                        self.step = self.step_ub
                    self._iter_best_config = self.trial_count
                    return
        proposed_by = self._proposed_by.get(trial_id)
        if proposed_by == self.incumbent:
            # proposed by current incumbent and no better
            self._num_complete4incumbent += 1
            cost = result.get(
                self.cost_attr) if result else self._trial_cost.get(trial_id)
            if cost:
                self._cost_complete4incumbent += cost
            if self._num_complete4incumbent >= 2 * self.dim and \
                    self._num_allowed4incumbent == 0:
                self._num_allowed4incumbent = 2
            if self._num_complete4incumbent == self.dir and (
                    not self._resource or self._resource == self.max_resource):
                # check stuck condition if using max resource
                if self.step >= self.step_lower_bound:
                    # decrease step size
                    self._oldK = self._K if self._K else self._iter_best_config
                    self._K = self.trial_count + 1
                    self.step *= np.sqrt(self._oldK / self._K)
                self._num_complete4incumbent -= 2
                if self._num_allowed4incumbent < 2:
                    self._num_allowed4incumbent = 2
        # elif proposed_by: del self._proposed_by[trial_id]

    def on_trial_result(self, trial_id: str, result: Dict):
        ''' early update of incumbent
        '''
        if result:
            obj = result.get(self._metric)
            if obj:
                obj *= self.metric_op
                if self.best_obj is None or obj < self.best_obj:
                    self.best_obj = obj
                    config = self._configs[trial_id]
                    if self.best_config != config:
                        self.best_config = config
                        if self._resource:
                            self._resource = config[self.prune_attr]
                        self.incumbent = self.normalize(self.best_config)
                        self.cost_incumbent = result.get(self.cost_attr)
                        self._cost_complete4incumbent = 0
                        self._num_complete4incumbent = 0
                        self._num_allowed4incumbent = 2 * self.dim
                        self._proposed_by.clear()
                        self._iter_best_config = self.trial_count
            cost = result.get(self.cost_attr)
            # record the cost in case it is pruned and cost info is lost
            self._trial_cost[trial_id] = cost

    def rand_vector_unit_sphere(self, dim) -> np.ndarray:
        vec = self._random.normal(0, 1, dim)
        mag = np.linalg.norm(vec)
        return vec / mag

    def suggest(self, trial_id: str) -> Optional[Dict]:
        ''' suggest a new config, one of the following cases:
        1. same incumbent, increase resource
        2. same resource, move from the incumbent to a random direction
        3. same resource, move from the incumbent to the opposite direction
        '''
        if self._num_complete4incumbent > 0 and self.cost_incumbent and \
            self._resource and self._resource < self.max_resource and (
                self._cost_complete4incumbent
                >= self.cost_incumbent * self.resource_multiple_factor):
            # consider increasing resource using sum eval cost of complete
            # configs
            self._resource = self._round(
                self._resource * self.resource_multiple_factor)
            config = self.best_config.copy()
            config[self.prune_attr] = self._resource
            self._direction_tried = None
            self._configs[trial_id] = config
            return config
        self._num_allowed4incumbent -= 1
        move = self.incumbent.copy()
        if self._direction_tried is not None:
            # return negative direction
            for i, key in enumerate(self._tunable_keys):
                move[key] -= self._direction_tried[i]
            self._direction_tried = None
        # propose a new direction
        self._direction_tried = self.rand_vector_unit_sphere(
            self.dim) * self.step
        for i, key in enumerate(self._tunable_keys):
            move[key] += self._direction_tried[i]
        self._project(move)
        config = self.denormalize(move)
        self._proposed_by[trial_id] = self.incumbent
        self._configs[trial_id] = config
        return unflatten_dict(config)

    def _project(self, config):
        ''' project normalized config in the feasible region and set prune_attr
        '''
        for key in self._bounded_keys:
            value = config[key]
            config[key] = max(0, min(1, value))
        if self._resource:
            config[self.prune_attr] = self._resource

    @property
    def can_suggest(self) -> bool:
        ''' can't suggest if 2*dim configs have been proposed for the incumbent
            while fewer are completed
        '''
        return self._num_allowed4incumbent > 0

    def config_signature(self, config) -> tuple:
        ''' return the signature tuple of a config
        '''
        config = flatten_dict(config)
        value_list = []
        for key in self._space_keys:
            if key in config:
                value = config[key]
                if key == self.prune_attr:
                    value_list.append(value)
                # else key must be in self.space
                # get rid of list type or constant,
                # e.g., "eval_metric": ["logloss", "error"]
                elif callable(getattr(self.space[key], 'sample', None)):
                    if isinstance(self.space[key], sample.Integer):
                        value_list.append(int(round(value)))
                    else:
                        value_list.append(value)
            else:
                value_list.append(None)
        return tuple(value_list)

    @property
    def converged(self) -> bool:
        ''' return whether the local search has converged
        '''
        if self._num_complete4incumbent < self.dir - 2:
            return False
        # check stepsize after enough configs are completed
        return self.step < self.step_lower_bound

    def reach(self, other: Searcher) -> bool:
        ''' whether the incumbent can reach the incumbent of other
        '''
        config1, config2 = self.best_config, other.best_config
        incumbent1, incumbent2 = self.incumbent, other.incumbent
        if self._resource and config1[self.prune_attr] > config2[self.prune_attr]:
            # resource will not decrease
            return False
        for key in self._unordered_cat_hp:
            # unordered cat choice is hard to reach by chance
            if config1[key] != config2[key]:
                return False
        delta = np.array(
            [incumbent1[key] - incumbent2[key] for key in self._tunable_keys])
        return np.linalg.norm(delta) <= self.step
