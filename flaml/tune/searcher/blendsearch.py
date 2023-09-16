# !
#  * Copyright (c) Microsoft Corporation. All rights reserved.
#  * Licensed under the MIT License. See LICENSE file in the
#  * project root for license information.
from typing import Dict, Optional, List, Tuple, Callable, Union
import numpy as np
import time
import pickle

try:
    from ray import __version__ as ray_version

    assert ray_version >= "1.10.0"
    if ray_version.startswith("1."):
        from ray.tune.suggest import Searcher
        from ray.tune.suggest.optuna import OptunaSearch as GlobalSearch
    else:
        from ray.tune.search import Searcher
        from ray.tune.search.optuna import OptunaSearch as GlobalSearch
except (ImportError, AssertionError):
    from .suggestion import Searcher
    from .suggestion import OptunaSearch as GlobalSearch
from ..trial import unflatten_dict, flatten_dict
from .. import INCUMBENT_RESULT
from .search_thread import SearchThread
from .flow2 import FLOW2
from ..space import add_cost_to_space, indexof, normalize, define_by_run_func
from ..result import TIME_TOTAL_S

import logging

SEARCH_THREAD_EPS = 1.0
PENALTY = 1e10  # penalty term for constraints
logger = logging.getLogger(__name__)


class BlendSearch(Searcher):
    """class for BlendSearch algorithm."""

    lagrange = "_lagrange"  # suffix for lagrange-modified metric
    LocalSearch = FLOW2

    def __init__(
        self,
        metric: Optional[str] = None,
        mode: Optional[str] = None,
        space: Optional[dict] = None,
        low_cost_partial_config: Optional[dict] = None,
        cat_hp_cost: Optional[dict] = None,
        points_to_evaluate: Optional[List[dict]] = None,
        evaluated_rewards: Optional[List] = None,
        time_budget_s: Union[int, float] = None,
        num_samples: Optional[int] = None,
        resource_attr: Optional[str] = None,
        min_resource: Optional[float] = None,
        max_resource: Optional[float] = None,
        reduction_factor: Optional[float] = None,
        global_search_alg: Optional[Searcher] = None,
        config_constraints: Optional[List[Tuple[Callable[[dict], float], str, float]]] = None,
        metric_constraints: Optional[List[Tuple[str, str, float]]] = None,
        seed: Optional[int] = 20,
        cost_attr: Optional[str] = "auto",
        cost_budget: Optional[float] = None,
        experimental: Optional[bool] = False,
        lexico_objectives: Optional[dict] = None,
        use_incumbent_result_in_evaluation=False,
        allow_empty_config=False,
    ):
        """Constructor.

        Args:
            metric: A string of the metric name to optimize for.
            mode: A string in ['min', 'max'] to specify the objective as
                minimization or maximization.
            space: A dictionary to specify the search space.
            low_cost_partial_config: A dictionary from a subset of
                controlled dimensions to the initial low-cost values.
                E.g., ```{'n_estimators': 4, 'max_leaves': 4}```.
            cat_hp_cost: A dictionary from a subset of categorical dimensions
                to the relative cost of each choice.
                E.g., ```{'tree_method': [1, 1, 2]}```.
                I.e., the relative cost of the three choices of 'tree_method'
                is 1, 1 and 2 respectively.
            points_to_evaluate: Initial parameter suggestions to be run first.
            evaluated_rewards (list): If you have previously evaluated the
                parameters passed in as points_to_evaluate you can avoid
                re-running those trials by passing in the reward attributes
                as a list so the optimiser can be told the results without
                needing to re-compute the trial. Must be the same or shorter length than
                points_to_evaluate. When provided, `mode` must be specified.
            time_budget_s: int or float | Time budget in seconds.
            num_samples: int | The number of configs to try. -1 means no limit on the
                number of configs to try.
            resource_attr: A string to specify the resource dimension and the best
                performance is assumed to be at the max_resource.
            min_resource: A float of the minimal resource to use for the resource_attr.
            max_resource: A float of the maximal resource to use for the resource_attr.
            reduction_factor: A float of the reduction factor used for
                incremental pruning.
            global_search_alg: A Searcher instance as the global search
                instance. If omitted, Optuna is used. The following algos have
                known issues when used as global_search_alg:
                - HyperOptSearch raises exception sometimes
                - TuneBOHB has its own scheduler
            config_constraints: A list of config constraints to be satisfied.
                E.g., ```config_constraints = [(mem_size, '<=', 1024**3)]```.
                `mem_size` is a function which produces a float number for the bytes
                needed for a config.
                It is used to skip configs which do not fit in memory.
            metric_constraints: A list of metric constraints to be satisfied.
                E.g., `['precision', '>=', 0.9]`. The sign can be ">=" or "<=".
            seed: An integer of the random seed.
            cost_attr: None or str to specify the attribute to evaluate the cost of different trials.
                Default is "auto", which means that we will automatically choose the cost attribute to use (depending
                on the nature of the resource budget). When cost_attr is set to None, cost differences between different trials will be omitted
                in our search algorithm. When cost_attr is set to a str different from "auto" and "time_total_s",
                this cost_attr must be available in the result dict of the trial.
            cost_budget: A float of the cost budget. Only valid when cost_attr is a str different from "auto" and "time_total_s".
            lexico_objectives: dict, default=None | It specifics information needed to perform multi-objective
                optimization with lexicographic preferences. This is only supported in CFO currently.
                When lexico_objectives is not None, the arguments metric, mode will be invalid.
                This dictionary shall contain the  following fields of key-value pairs:
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
            experimental: A bool of whether to use experimental features.
        """
        self._eps = SEARCH_THREAD_EPS
        self._input_cost_attr = cost_attr
        if cost_attr == "auto":
            if time_budget_s is not None:
                self.cost_attr = TIME_TOTAL_S
            else:
                self.cost_attr = None
            self._cost_budget = None
        else:
            self.cost_attr = cost_attr
            self._cost_budget = cost_budget
        self.penalty = PENALTY  # penalty term for constraints
        self._metric, self._mode = metric, mode
        self._use_incumbent_result_in_evaluation = use_incumbent_result_in_evaluation
        self.lexico_objectives = lexico_objectives
        init_config = low_cost_partial_config or {}
        if not init_config:
            logger.info(
                "No low-cost partial config given to the search algorithm. "
                "For cost-frugal search, "
                "consider providing low-cost values for cost-related hps via "
                "'low_cost_partial_config'. More info can be found at "
                "https://microsoft.github.io/FLAML/docs/FAQ#about-low_cost_partial_config-in-tune"
            )
        if evaluated_rewards:
            assert mode, "mode must be specified when evaluted_rewards is provided."
            self._points_to_evaluate = []
            self._evaluated_rewards = []
            n = len(evaluated_rewards)
            self._evaluated_points = points_to_evaluate[:n]
            new_points_to_evaluate = points_to_evaluate[n:]
            self._all_rewards = evaluated_rewards
            best = max(evaluated_rewards) if mode == "max" else min(evaluated_rewards)
            # only keep the best points as start points
            for i, r in enumerate(evaluated_rewards):
                if r == best:
                    p = points_to_evaluate[i]
                    self._points_to_evaluate.append(p)
                    self._evaluated_rewards.append(r)
            self._points_to_evaluate.extend(new_points_to_evaluate)
        else:
            self._points_to_evaluate = points_to_evaluate or []
            self._evaluated_rewards = evaluated_rewards or []
        self._config_constraints = config_constraints
        self._metric_constraints = metric_constraints
        if metric_constraints:
            assert all(x[1] in ["<=", ">="] for x in metric_constraints), "sign of metric constraints must be <= or >=."
            # metric modified by lagrange
            metric += self.lagrange
        self._cat_hp_cost = cat_hp_cost or {}
        if space:
            add_cost_to_space(space, init_config, self._cat_hp_cost)
        self._ls = self.LocalSearch(
            init_config,
            metric,
            mode,
            space,
            resource_attr,
            min_resource,
            max_resource,
            reduction_factor,
            self.cost_attr,
            seed,
            self.lexico_objectives,
        )
        if global_search_alg is not None:
            self._gs = global_search_alg
        elif getattr(self, "__name__", None) != "CFO":
            if space and self._ls.hierarchical:
                from functools import partial

                gs_space = partial(define_by_run_func, space=space)
                evaluated_rewards = None  # not supported by define-by-run
            else:
                gs_space = space
            gs_seed = seed - 10 if (seed - 10) >= 0 else seed - 11 + (1 << 32)
            self._gs_seed = gs_seed
            if experimental:
                import optuna as ot

                sampler = ot.samplers.TPESampler(seed=gs_seed, multivariate=True, group=True)
            else:
                sampler = None
            try:
                assert evaluated_rewards
                self._gs = GlobalSearch(
                    space=gs_space,
                    metric=metric,
                    mode=mode,
                    seed=gs_seed,
                    sampler=sampler,
                    points_to_evaluate=self._evaluated_points,
                    evaluated_rewards=evaluated_rewards,
                )
            except (AssertionError, ValueError):
                self._gs = GlobalSearch(
                    space=gs_space,
                    metric=metric,
                    mode=mode,
                    seed=gs_seed,
                    sampler=sampler,
                )
            self._gs.space = space
        else:
            self._gs = None
        self._experimental = experimental
        if getattr(self, "__name__", None) == "CFO" and points_to_evaluate and len(self._points_to_evaluate) > 1:
            # use the best config in points_to_evaluate as the start point
            self._candidate_start_points = {}
            self._started_from_low_cost = not low_cost_partial_config
        else:
            self._candidate_start_points = None
        self._time_budget_s, self._num_samples = time_budget_s, num_samples
        self._allow_empty_config = allow_empty_config
        if space is not None:
            self._init_search()

    def set_search_properties(
        self,
        metric: Optional[str] = None,
        mode: Optional[str] = None,
        config: Optional[Dict] = None,
        **spec,
    ) -> bool:
        metric_changed = mode_changed = False
        if metric and self._metric != metric:
            metric_changed = True
            self._metric = metric
            if self._metric_constraints:
                # metric modified by lagrange
                metric += self.lagrange
                # TODO: don't change metric for global search methods that
                # can handle constraints already
        if mode and self._mode != mode:
            mode_changed = True
            self._mode = mode
        if not self._ls.space:
            # the search space can be set only once
            if self._gs is not None:
                # define-by-run is not supported via set_search_properties
                self._gs.set_search_properties(metric, mode, config)
                self._gs.space = config
            if config:
                add_cost_to_space(config, self._ls.init_config, self._cat_hp_cost)
            self._ls.set_search_properties(metric, mode, config)
            self._init_search()
        else:
            if metric_changed or mode_changed:
                # reset search when metric or mode changed
                self._ls.set_search_properties(metric, mode)
                if self._gs is not None:
                    self._gs = GlobalSearch(
                        space=self._gs._space,
                        metric=metric,
                        mode=mode,
                        seed=self._gs_seed,
                    )
                    self._gs.space = self._ls.space
                self._init_search()
        if spec:
            # CFO doesn't need these settings
            if "time_budget_s" in spec:
                self._time_budget_s = spec["time_budget_s"]  # budget from now
                now = time.time()
                self._time_used += now - self._start_time
                self._start_time = now
                self._set_deadline()
                if self._input_cost_attr == "auto" and self._time_budget_s:
                    self.cost_attr = self._ls.cost_attr = TIME_TOTAL_S
            if "metric_target" in spec:
                self._metric_target = spec.get("metric_target")
            num_samples = spec.get("num_samples")
            if num_samples is not None:
                self._num_samples = (
                    (num_samples + len(self._result) + len(self._trial_proposed_by))
                    if num_samples > 0  # 0 is currently treated the same as -1
                    else num_samples
                )
        return True

    def _set_deadline(self):
        if self._time_budget_s is not None:
            self._deadline = self._time_budget_s + self._start_time
            self._set_eps()
        else:
            self._deadline = np.inf

    def _set_eps(self):
        """set eps for search threads according to time budget"""
        self._eps = max(min(self._time_budget_s / 1000.0, 1.0), 1e-9)

    def _init_search(self):
        """initialize the search"""
        self._start_time = time.time()
        self._time_used = 0
        self._set_deadline()
        self._is_ls_ever_converged = False
        self._subspace = {}  # the subspace for each trial id
        self._metric_target = np.inf * self._ls.metric_op
        self._search_thread_pool = {
            # id: int -> thread: SearchThread
            0: SearchThread(self._ls.mode, self._gs, self.cost_attr, self._eps)
        }
        self._thread_count = 1  # total # threads created
        self._init_used = self._ls.init_config is None
        self._trial_proposed_by = {}  # trial_id: str -> thread_id: int
        self._ls_bound_min = normalize(
            self._ls.init_config.copy(),
            self._ls.space,
            self._ls.init_config,
            {},
            recursive=True,
        )
        self._ls_bound_max = normalize(
            self._ls.init_config.copy(),
            self._ls.space,
            self._ls.init_config,
            {},
            recursive=True,
        )
        self._gs_admissible_min = self._ls_bound_min.copy()
        self._gs_admissible_max = self._ls_bound_max.copy()

        if self._metric_constraints:
            self._metric_constraint_satisfied = False
            self._metric_constraint_penalty = [self.penalty for _ in self._metric_constraints]
        else:
            self._metric_constraint_satisfied = True
            self._metric_constraint_penalty = None
        self.best_resource = self._ls.min_resource
        i = 0
        # config_signature: tuple -> result: Dict
        self._result = {}
        self._cost_used = 0
        while self._evaluated_rewards:
            # go over the evaluated rewards
            trial_id = f"trial_for_evaluated_{i}"
            self.suggest(trial_id)
            i += 1

    def save(self, checkpoint_path: str):
        """save states to a checkpoint path."""
        self._time_used += time.time() - self._start_time
        self._start_time = time.time()
        save_object = self
        with open(checkpoint_path, "wb") as outputFile:
            pickle.dump(save_object, outputFile)

    def restore(self, checkpoint_path: str):
        """restore states from checkpoint."""
        with open(checkpoint_path, "rb") as inputFile:
            state = pickle.load(inputFile)
        self.__dict__ = state.__dict__
        self._start_time = time.time()
        self._set_deadline()

    @property
    def metric_target(self):
        return self._metric_target

    @property
    def is_ls_ever_converged(self):
        return self._is_ls_ever_converged

    def on_trial_complete(self, trial_id: str, result: Optional[Dict] = None, error: bool = False):
        """search thread updater and cleaner."""
        metric_constraint_satisfied = True
        if result and not error and self._metric_constraints:
            # account for metric constraints if any
            objective = result[self._metric]
            for i, constraint in enumerate(self._metric_constraints):
                metric_constraint, sign, threshold = constraint
                value = result.get(metric_constraint)
                if value:
                    sign_op = 1 if sign == "<=" else -1
                    violation = (value - threshold) * sign_op
                    if violation > 0:
                        # add penalty term to the metric
                        objective += self._metric_constraint_penalty[i] * violation * self._ls.metric_op
                        metric_constraint_satisfied = False
                        if self._metric_constraint_penalty[i] < self.penalty:
                            self._metric_constraint_penalty[i] += violation
            result[self._metric + self.lagrange] = objective
            if metric_constraint_satisfied and not self._metric_constraint_satisfied:
                # found a feasible point
                self._metric_constraint_penalty = [1 for _ in self._metric_constraints]
            self._metric_constraint_satisfied |= metric_constraint_satisfied
        thread_id = self._trial_proposed_by.get(trial_id)
        if thread_id in self._search_thread_pool:
            self._search_thread_pool[thread_id].on_trial_complete(trial_id, result, error)
            del self._trial_proposed_by[trial_id]
        if result:
            config = result.get("config", {})
            if not config:
                for key, value in result.items():
                    if key.startswith("config/"):
                        config[key[7:]] = value
            if self._allow_empty_config and not config:
                return
            signature = self._ls.config_signature(config, self._subspace.get(trial_id, {}))
            if error:  # remove from result cache
                del self._result[signature]
            else:  # add to result cache
                self._cost_used += result.get(self.cost_attr, 0)
                self._result[signature] = result
                # update target metric if improved
                objective = result[self._ls.metric]
                if (objective - self._metric_target) * self._ls.metric_op < 0:
                    self._metric_target = objective
                    if self._ls.resource:
                        self._best_resource = config[self._ls.resource_attr]
                if thread_id:
                    if not self._metric_constraint_satisfied:
                        # no point has been found to satisfy metric constraint
                        self._expand_admissible_region(
                            self._ls_bound_min,
                            self._ls_bound_max,
                            self._subspace.get(trial_id, self._ls.space),
                        )
                    if self._gs is not None and self._experimental and (not self._ls.hierarchical):
                        self._gs.add_evaluated_point(flatten_dict(config), objective)
                        # TODO: recover when supported
                        # converted = convert_key(config, self._gs.space)
                        # logger.info(converted)
                        # self._gs.add_evaluated_point(converted, objective)
                elif metric_constraint_satisfied and self._create_condition(result):
                    # thread creator
                    thread_id = self._thread_count
                    self._started_from_given = self._candidate_start_points and trial_id in self._candidate_start_points
                    if self._started_from_given:
                        del self._candidate_start_points[trial_id]
                    else:
                        self._started_from_low_cost = True
                    self._create_thread(config, result, self._subspace.get(trial_id, self._ls.space))
                # reset admissible region to ls bounding box
                self._gs_admissible_min.update(self._ls_bound_min)
                self._gs_admissible_max.update(self._ls_bound_max)
        # cleaner
        if thread_id and thread_id in self._search_thread_pool:
            # local search thread
            self._clean(thread_id)
        if trial_id in self._subspace and not (
            self._candidate_start_points and trial_id in self._candidate_start_points
        ):
            del self._subspace[trial_id]

    def _create_thread(self, config, result, space):
        if self.lexico_objectives is None:
            obj = result[self._ls.metric]
        else:
            obj = {k: result[k] for k in self.lexico_objectives["metrics"]}
        self._search_thread_pool[self._thread_count] = SearchThread(
            self._ls.mode,
            self._ls.create(
                config,
                obj,
                cost=result.get(self.cost_attr, 1),
                space=space,
            ),
            self.cost_attr,
            self._eps,
        )
        self._thread_count += 1
        self._update_admissible_region(
            unflatten_dict(config),
            self._ls_bound_min,
            self._ls_bound_max,
            space,
            self._ls.space,
        )

    def _update_admissible_region(
        self,
        config,
        admissible_min,
        admissible_max,
        subspace: Dict = {},
        space: Dict = {},
    ):
        # update admissible region
        normalized_config = normalize(config, subspace, config, {})
        for key in admissible_min:
            value = normalized_config[key]
            if isinstance(admissible_max[key], list):
                domain = space[key]
                choice = indexof(domain, value)
                self._update_admissible_region(
                    value,
                    admissible_min[key][choice],
                    admissible_max[key][choice],
                    subspace[key],
                    domain[choice],
                )
                if len(admissible_max[key]) > len(domain.categories):
                    # points + index
                    normal = (choice + 0.5) / len(domain.categories)
                    admissible_max[key][-1] = max(normal, admissible_max[key][-1])
                    admissible_min[key][-1] = min(normal, admissible_min[key][-1])
            elif isinstance(value, dict):
                self._update_admissible_region(
                    value,
                    admissible_min[key],
                    admissible_max[key],
                    subspace[key],
                    space[key],
                )
            else:
                if value > admissible_max[key]:
                    admissible_max[key] = value
                elif value < admissible_min[key]:
                    admissible_min[key] = value

    def _create_condition(self, result: Dict) -> bool:
        """create thread condition"""
        if len(self._search_thread_pool) < 2:
            return True
        obj_median = np.median([thread.obj_best1 for id, thread in self._search_thread_pool.items() if id])
        return result[self._ls.metric] * self._ls.metric_op < obj_median

    def _clean(self, thread_id: int):
        """delete thread and increase admissible region if converged,
        merge local threads if they are close
        """
        assert thread_id
        todelete = set()
        for id in self._search_thread_pool:
            if id and id != thread_id:
                if self._inferior(id, thread_id):
                    todelete.add(id)
        for id in self._search_thread_pool:
            if id and id != thread_id:
                if self._inferior(thread_id, id):
                    todelete.add(thread_id)
                    break
        create_new = False
        if self._search_thread_pool[thread_id].converged:
            self._is_ls_ever_converged = True
            todelete.add(thread_id)
            self._expand_admissible_region(
                self._ls_bound_min,
                self._ls_bound_max,
                self._search_thread_pool[thread_id].space,
            )
            if self._candidate_start_points:
                if not self._started_from_given:
                    # remove start points whose perf is worse than the converged
                    obj = self._search_thread_pool[thread_id].obj_best1
                    worse = [
                        trial_id
                        for trial_id, r in self._candidate_start_points.items()
                        if r and r[self._ls.metric] * self._ls.metric_op >= obj
                    ]
                    # logger.info(f"remove candidate start points {worse} than {obj}")
                    for trial_id in worse:
                        del self._candidate_start_points[trial_id]
                if self._candidate_start_points and self._started_from_low_cost:
                    create_new = True
        for id in todelete:
            del self._search_thread_pool[id]
        if create_new:
            self._create_thread_from_best_candidate()

    def _create_thread_from_best_candidate(self):
        # find the best start point
        best_trial_id = None
        obj_best = None
        for trial_id, r in self._candidate_start_points.items():
            if r and (best_trial_id is None or r[self._ls.metric] * self._ls.metric_op < obj_best):
                best_trial_id = trial_id
                obj_best = r[self._ls.metric] * self._ls.metric_op
        if best_trial_id:
            # create a new thread
            config = {}
            result = self._candidate_start_points[best_trial_id]
            for key, value in result.items():
                if key.startswith("config/"):
                    config[key[7:]] = value
            self._started_from_given = True
            del self._candidate_start_points[best_trial_id]
            self._create_thread(config, result, self._subspace.get(best_trial_id, self._ls.space))

    def _expand_admissible_region(self, lower, upper, space):
        """expand the admissible region for the subspace `space`"""
        for key in upper:
            ub = upper[key]
            if isinstance(ub, list):
                choice = space[key].get("_choice_")
                if choice:
                    self._expand_admissible_region(lower[key][choice], upper[key][choice], space[key])
            elif isinstance(ub, dict):
                self._expand_admissible_region(lower[key], ub, space[key])
            else:
                upper[key] += self._ls.STEPSIZE
                lower[key] -= self._ls.STEPSIZE

    def _inferior(self, id1: int, id2: int) -> bool:
        """whether thread id1 is inferior to id2"""
        t1 = self._search_thread_pool[id1]
        t2 = self._search_thread_pool[id2]
        if t1.obj_best1 < t2.obj_best2:
            return False
        elif t1.resource and t1.resource < t2.resource:
            return False
        elif t2.reach(t1):
            return True
        return False

    def on_trial_result(self, trial_id: str, result: Dict):
        """receive intermediate result."""
        if trial_id not in self._trial_proposed_by:
            return
        thread_id = self._trial_proposed_by[trial_id]
        if thread_id not in self._search_thread_pool:
            return
        if result and self._metric_constraints:
            result[self._metric + self.lagrange] = result[self._metric]
        self._search_thread_pool[thread_id].on_trial_result(trial_id, result)

    def suggest(self, trial_id: str) -> Optional[Dict]:
        """choose thread, suggest a valid config."""
        if self._init_used and not self._points_to_evaluate:
            if self._cost_budget and self._cost_used >= self._cost_budget:
                return None
            choice, backup = self._select_thread()
            config = self._search_thread_pool[choice].suggest(trial_id)
            if not choice and config is not None and self._ls.resource:
                config[self._ls.resource_attr] = self.best_resource
            elif choice and config is None:
                # local search thread finishes
                if self._search_thread_pool[choice].converged:
                    self._expand_admissible_region(
                        self._ls_bound_min,
                        self._ls_bound_max,
                        self._search_thread_pool[choice].space,
                    )
                    del self._search_thread_pool[choice]
                return
            # preliminary check; not checking config validation
            space = self._search_thread_pool[choice].space
            skip = self._should_skip(choice, trial_id, config, space)
            use_rs = 0
            if skip:
                if choice:
                    return
                # use rs when BO fails to suggest a config
                config, space = self._ls.complete_config({})
                skip = self._should_skip(-1, trial_id, config, space)
                if skip:
                    return
                use_rs = 1
            if choice or self._valid(
                config,
                self._ls.space,
                space,
                self._gs_admissible_min,
                self._gs_admissible_max,
            ):
                # LS or valid or no backup choice
                self._trial_proposed_by[trial_id] = choice
                self._search_thread_pool[choice].running += use_rs
            else:  # invalid config proposed by GS
                if choice == backup:
                    # use CFO's init point
                    init_config = self._ls.init_config
                    config, space = self._ls.complete_config(init_config, self._ls_bound_min, self._ls_bound_max)
                    self._trial_proposed_by[trial_id] = choice
                    self._search_thread_pool[choice].running += 1
                else:
                    thread = self._search_thread_pool[backup]
                    config = thread.suggest(trial_id)
                    space = thread.space
                    skip = self._should_skip(backup, trial_id, config, space)
                    if skip:
                        return
                    self._trial_proposed_by[trial_id] = backup
                    choice = backup
            if not choice:  # global search
                # temporarily relax admissible region for parallel proposals
                self._update_admissible_region(
                    config,
                    self._gs_admissible_min,
                    self._gs_admissible_max,
                    space,
                    self._ls.space,
                )
            else:
                self._update_admissible_region(
                    config,
                    self._ls_bound_min,
                    self._ls_bound_max,
                    space,
                    self._ls.space,
                )
                self._gs_admissible_min.update(self._ls_bound_min)
                self._gs_admissible_max.update(self._ls_bound_max)
            signature = self._ls.config_signature(config, space)
            self._result[signature] = {}
            self._subspace[trial_id] = space
        else:  # use init config
            if self._candidate_start_points is not None and self._points_to_evaluate:
                self._candidate_start_points[trial_id] = None
            reward = None
            if self._points_to_evaluate:
                init_config = self._points_to_evaluate.pop(0)
                if self._evaluated_rewards:
                    reward = self._evaluated_rewards.pop(0)
            else:
                init_config = self._ls.init_config
            if self._allow_empty_config and not init_config:
                assert reward is None, "Empty config can't have reward."
                return init_config
            config, space = self._ls.complete_config(init_config, self._ls_bound_min, self._ls_bound_max)
            config_signature = self._ls.config_signature(config, space)
            if reward is None:
                result = self._result.get(config_signature)
                if result:  # tried before
                    return
                elif result is None:  # not tried before
                    if self._violate_config_constriants(config, config_signature):
                        # violate config constraints
                        return
                    self._result[config_signature] = {}
                else:  # running but no result yet
                    return
            self._init_used = True
            self._trial_proposed_by[trial_id] = 0
            self._search_thread_pool[0].running += 1
            self._subspace[trial_id] = space
            if reward is not None:
                result = {self._metric: reward, self.cost_attr: 1, "config": config}
                # result = self._result[config_signature]
                self.on_trial_complete(trial_id, result)
                return
        if self._use_incumbent_result_in_evaluation:
            if self._trial_proposed_by[trial_id] > 0:
                choice_thread = self._search_thread_pool[self._trial_proposed_by[trial_id]]
                config[INCUMBENT_RESULT] = choice_thread.best_result
        return config

    def _violate_config_constriants(self, config, config_signature):
        """check if config violates config constraints.
        If so, set the result to worst and return True.
        """
        if not self._config_constraints:
            return False
        for constraint in self._config_constraints:
            func, sign, threshold = constraint
            value = func(config)
            if (
                sign == "<="
                and value > threshold
                or sign == ">="
                and value < threshold
                or sign == ">"
                and value <= threshold
                or sign == "<"
                and value > threshold
            ):
                self._result[config_signature] = {
                    self._metric: np.inf * self._ls.metric_op,
                    "time_total_s": 1,
                }
                return True
        return False

    def _should_skip(self, choice, trial_id, config, space) -> bool:
        """if config is None or config's result is known or constraints are violated
        return True; o.w. return False
        """
        if config is None:
            return True
        config_signature = self._ls.config_signature(config, space)
        exists = config_signature in self._result
        if not exists:
            # check constraints
            exists = self._violate_config_constriants(config, config_signature)
        if exists:  # suggested before (including violate constraints)
            if choice >= 0:  # not fallback to rs
                result = self._result.get(config_signature)
                if result:  # finished
                    self._search_thread_pool[choice].on_trial_complete(trial_id, result, error=False)
                    if choice:
                        # local search thread
                        self._clean(choice)
                # else:     # running
                #     # tell the thread there is an error
                #     self._search_thread_pool[choice].on_trial_complete(
                #         trial_id, {}, error=True)
            return True
        return False

    def _select_thread(self) -> Tuple:
        """thread selector; use can_suggest to check LS availability"""
        # calculate min_eci according to the budget left
        min_eci = np.inf
        if self.cost_attr == TIME_TOTAL_S:
            now = time.time()
            min_eci = self._deadline - now
            if min_eci <= 0:
                # return -1, -1
                # keep proposing new configs assuming no budget left
                min_eci = 0
            elif self._num_samples and self._num_samples > 0:
                # estimate time left according to num_samples limitation
                num_finished = len(self._result)
                num_proposed = num_finished + len(self._trial_proposed_by)
                num_left = max(self._num_samples - num_proposed, 0)
                if num_proposed > 0:
                    time_used = now - self._start_time + self._time_used
                    min_eci = min(min_eci, time_used / num_finished * num_left)
                # print(f"{min_eci}, {time_used / num_finished * num_left}, {num_finished}, {num_left}")
        elif self.cost_attr is not None and self._cost_budget:
            min_eci = max(self._cost_budget - self._cost_used, 0)
        elif self._num_samples and self._num_samples > 0:
            num_finished = len(self._result)
            num_proposed = num_finished + len(self._trial_proposed_by)
            min_eci = max(self._num_samples - num_proposed, 0)
        # update priority
        max_speed = 0
        for thread in self._search_thread_pool.values():
            if thread.speed > max_speed:
                max_speed = thread.speed
        for thread in self._search_thread_pool.values():
            thread.update_eci(self._metric_target, max_speed)
            if thread.eci < min_eci:
                min_eci = thread.eci
        for thread in self._search_thread_pool.values():
            thread.update_priority(min_eci)

        top_thread_id = backup_thread_id = 0
        priority1 = priority2 = self._search_thread_pool[0].priority
        for thread_id, thread in self._search_thread_pool.items():
            if thread_id and thread.can_suggest:
                priority = thread.priority
                if priority > priority1:
                    priority1 = priority
                    top_thread_id = thread_id
                if priority > priority2 or backup_thread_id == 0:
                    priority2 = priority
                    backup_thread_id = thread_id
        return top_thread_id, backup_thread_id

    def _valid(self, config: Dict, space: Dict, subspace: Dict, lower: Dict, upper: Dict) -> bool:
        """config validator"""
        normalized_config = normalize(config, subspace, config, {})
        for key, lb in lower.items():
            if key in config:
                value = normalized_config[key]
                if isinstance(lb, list):
                    domain = space[key]
                    index = indexof(domain, value)
                    nestedspace = subspace[key]
                    lb = lb[index]
                    ub = upper[key][index]
                elif isinstance(lb, dict):
                    nestedspace = subspace[key]
                    domain = space[key]
                    ub = upper[key]
                else:
                    nestedspace = None
                if nestedspace:
                    valid = self._valid(value, domain, nestedspace, lb, ub)
                    if not valid:
                        return False
                elif value + self._ls.STEPSIZE < lower[key] or value > upper[key] + self._ls.STEPSIZE:
                    return False
        return True

    @property
    def results(self) -> List[Dict]:
        """A list of dicts of results for each evaluated configuration.

        Each dict has "config" and metric names as keys.
        The returned dict includes the initial results provided via `evaluated_reward`.
        """
        return [x for x in getattr(self, "_result", {}).values() if x]


try:
    from ray import __version__ as ray_version

    assert ray_version >= "1.10.0"
    from ray.tune import (
        uniform,
        quniform,
        choice,
        randint,
        qrandint,
        randn,
        qrandn,
        loguniform,
        qloguniform,
    )
except (ImportError, AssertionError):
    from ..sample import (
        uniform,
        quniform,
        choice,
        randint,
        qrandint,
        randn,
        qrandn,
        loguniform,
        qloguniform,
    )

try:
    from nni.tuner import Tuner as NNITuner
    from nni.utils import extract_scalar_reward
except ImportError:
    NNITuner = object

    def extract_scalar_reward(x: Dict):
        return x.get("default")


class BlendSearchTuner(BlendSearch, NNITuner):
    """Tuner class for NNI."""

    def receive_trial_result(self, parameter_id, parameters, value, **kwargs):
        """Receive trial's final result.

        Args:
            parameter_id: int.
            parameters: object created by `generate_parameters()`.
            value: final metrics of the trial, including default metric.
        """
        result = {
            "config": parameters,
            self._metric: extract_scalar_reward(value),
            self.cost_attr: 1 if isinstance(value, float) else value.get(self.cost_attr, value.get("sequence", 1))
            # if nni does not report training cost,
            # using sequence as an approximation.
            # if no sequence, using a constant 1
        }
        self.on_trial_complete(str(parameter_id), result)

    ...

    def generate_parameters(self, parameter_id, **kwargs) -> Dict:
        """Returns a set of trial (hyper-)parameters, as a serializable object.

        Args:
            parameter_id: int.
        """
        return self.suggest(str(parameter_id))

    ...

    def update_search_space(self, search_space):
        """Required by NNI.

        Tuners are advised to support updating search space at run-time.
        If a tuner can only set search space once before generating first hyper-parameters,
        it should explicitly document this behaviour.

        Args:
            search_space: JSON object created by experiment owner.
        """
        config = {}
        for key, value in search_space.items():
            v = value.get("_value")
            _type = value["_type"]
            if _type == "choice":
                config[key] = choice(v)
            elif _type == "randint":
                config[key] = randint(*v)
            elif _type == "uniform":
                config[key] = uniform(*v)
            elif _type == "quniform":
                config[key] = quniform(*v)
            elif _type == "loguniform":
                config[key] = loguniform(*v)
            elif _type == "qloguniform":
                config[key] = qloguniform(*v)
            elif _type == "normal":
                config[key] = randn(*v)
            elif _type == "qnormal":
                config[key] = qrandn(*v)
            else:
                raise ValueError(f"unsupported type in search_space {_type}")
        # low_cost_partial_config is passed to constructor,
        # which is before update_search_space() is called
        init_config = self._ls.init_config
        add_cost_to_space(config, init_config, self._cat_hp_cost)
        self._ls = self.LocalSearch(
            init_config,
            self._ls.metric,
            self._mode,
            config,
            self._ls.resource_attr,
            self._ls.min_resource,
            self._ls.max_resource,
            self._ls.resource_multiple_factor,
            cost_attr=self.cost_attr,
            seed=self._ls.seed,
            lexico_objectives=self.lexico_objectives,
        )
        if self._gs is not None:
            self._gs = GlobalSearch(
                space=config,
                metric=self._metric,
                mode=self._mode,
                sampler=self._gs._sampler,
            )
            self._gs.space = config
        self._init_search()


class CFO(BlendSearchTuner):
    """class for CFO algorithm."""

    __name__ = "CFO"

    def suggest(self, trial_id: str) -> Optional[Dict]:
        # Number of threads is 1 or 2. Thread 0 is a vacuous thread
        assert len(self._search_thread_pool) < 3, len(self._search_thread_pool)
        if len(self._search_thread_pool) < 2:
            # When a local thread converges, the number of threads is 1
            # Need to restart
            self._init_used = False
        return super().suggest(trial_id)

    def _select_thread(self) -> Tuple:
        for key in self._search_thread_pool:
            if key:
                return key, key

    def _create_condition(self, result: Dict) -> bool:
        """create thread condition"""
        if self._points_to_evaluate:
            # still evaluating user-specified init points
            # we evaluate all candidate start points before we
            # create the first local search thread
            return False
        if len(self._search_thread_pool) == 2:
            return False
        if self._candidate_start_points and self._thread_count == 1:
            # result needs to match or exceed the best candidate start point
            obj_best = min(
                (self._ls.metric_op * r[self._ls.metric] for r in self._candidate_start_points.values() if r),
                default=-np.inf,
            )

            return result[self._ls.metric] * self._ls.metric_op <= obj_best
        else:
            return True

    def on_trial_complete(self, trial_id: str, result: Optional[Dict] = None, error: bool = False):
        super().on_trial_complete(trial_id, result, error)
        if self._candidate_start_points and trial_id in self._candidate_start_points:
            # the trial is a candidate start point
            self._candidate_start_points[trial_id] = result
            if len(self._search_thread_pool) < 2 and not self._points_to_evaluate:
                self._create_thread_from_best_candidate()


class RandomSearch(CFO):
    """Class for random search."""

    def suggest(self, trial_id: str) -> Optional[Dict]:
        if self._points_to_evaluate:
            return super().suggest(trial_id)
        config, _ = self._ls.complete_config({})
        return config

    def on_trial_complete(self, trial_id: str, result: Optional[Dict] = None, error: bool = False):
        return

    def on_trial_result(self, trial_id: str, result: Dict):
        return
