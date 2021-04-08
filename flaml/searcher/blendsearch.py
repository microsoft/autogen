'''!
 * Copyright (c) 2020-2021 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in the
 * project root for license information.
'''
from typing import Dict, Optional, List, Tuple, Callable
import numpy as np
import time
import pickle

try:
    from ray.tune.suggest import Searcher
    from ray.tune.suggest.optuna import OptunaSearch as GlobalSearch
    from ray.tune.suggest.variant_generator import generate_variants
except ImportError:
    from .suggestion import Searcher, OptunaSearch as GlobalSearch
    from .variant_generator import generate_variants
from .search_thread import SearchThread
from .flow2 import FLOW2 as LocalSearch

import logging
logger = logging.getLogger(__name__)


class BlendSearch(Searcher):
    '''class for BlendSearch algorithm
    '''

    cost_attr = "time_total_s"  # cost attribute in result

    def __init__(self,
                 metric: Optional[str] = None,
                 mode: Optional[str] = None,
                 space: Optional[dict] = None,
                 points_to_evaluate: Optional[List[dict]] = None,
                 low_cost_partial_config: Optional[dict] = None,
                 cat_hp_cost: Optional[dict] = None,
                 prune_attr: Optional[str] = None,
                 min_resource: Optional[float] = None,
                 max_resource: Optional[float] = None,
                 reduction_factor: Optional[float] = None,
                 resources_per_trial: Optional[dict] = None,
                 global_search_alg: Optional[Searcher] = None,
                 mem_size: Callable[[dict], float] = None,
                 seed: Optional[int] = 20):
        '''Constructor

        Args:
            metric: A string of the metric name to optimize for.
                minimization or maximization.
            mode: A string in ['min', 'max'] to specify the objective as
            space: A dictionary to specify the search space.
            points_to_evaluate: Initial parameter suggestions to be run first.
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
                three choices of 'tree_method' is 1, 1 and 2 respectively.
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
            reduction_factor: A float of the reduction factor used for
                incremental pruning.
            resources_per_trial: A dictionary of the resources permitted per
                trial, such as 'mem'.
            global_search_alg: A Searcher instance as the global search
                instance. If omitted, Optuna is used. The following algos have
                known issues when used as global_search_alg:
                - HyperOptSearch raises exception sometimes
                - TuneBOHB has its own scheduler
            mem_size: A function to estimate the memory size for a given config.
            seed: An integer of the random seed.
        '''
        self._metric, self._mode = metric, mode
        init_config = low_cost_partial_config or {}
        self._points_to_evaluate = points_to_evaluate or []
        if global_search_alg is not None:
            self._gs = global_search_alg
        elif getattr(self, '__name__', None) != 'CFO':
            self._gs = GlobalSearch(space=space, metric=metric, mode=mode)
        else:
            self._gs = None
        self._ls = LocalSearch(
            init_config, metric, mode, cat_hp_cost, space,
            prune_attr, min_resource, max_resource, reduction_factor, seed)
        self._resources_per_trial = resources_per_trial
        self._mem_size = mem_size
        self._mem_threshold = resources_per_trial.get(
            'mem') if resources_per_trial else None
        self._init_search()

    def set_search_properties(self,
                              metric: Optional[str] = None,
                              mode: Optional[str] = None,
                              config: Optional[Dict] = None) -> bool:
        if self._ls.space:
            if 'time_budget_s' in config:
                self._deadline = config.get('time_budget_s') + time.time()
            if 'metric_target' in config:
                self._metric_target = config.get('metric_target')
        else:
            if metric:
                self._metric = metric
            if mode:
                self._mode = mode
            self._ls.set_search_properties(metric, mode, config)
            if self._gs is not None:
                self._gs.set_search_properties(metric, mode, config)
            self._init_search()
        return True

    def _init_search(self):
        '''initialize the search
        '''
        self._metric_target = np.inf * self._ls.metric_op
        self._search_thread_pool = {
            # id: int -> thread: SearchThread
            0: SearchThread(self._ls.mode, self._gs)
        }
        self._thread_count = 1  # total # threads created
        self._init_used = self._ls.init_config is None
        self._trial_proposed_by = {}  # trial_id: str -> thread_id: int
        self._ls_bound_min = self._ls.normalize(self._ls.init_config)
        self._ls_bound_max = self._ls_bound_min.copy()
        self._gs_admissible_min = self._ls_bound_min.copy()
        self._gs_admissible_max = self._ls_bound_max.copy()
        self._result = {}  # config_signature: tuple -> result: Dict
        self._deadline = np.inf

    def save(self, checkpoint_path: str):
        save_object = self
        with open(checkpoint_path, "wb") as outputFile:
            pickle.dump(save_object, outputFile)

    def restore(self, checkpoint_path: str):
        with open(checkpoint_path, "rb") as inputFile:
            state = pickle.load(inputFile)
        self._metric_target = state._metric_target
        self._search_thread_pool = state._search_thread_pool
        self._thread_count = state._thread_count
        self._init_used = state._init_used
        self._trial_proposed_by = state._trial_proposed_by
        self._ls_bound_min = state._ls_bound_min
        self._ls_bound_max = state._ls_bound_max
        self._gs_admissible_min = state._gs_admissible_min
        self._gs_admissible_max = state._gs_admissible_max
        self._result = state._result
        self._deadline = state._deadline
        self._metric, self._mode = state._metric, state._mode
        self._points_to_evaluate = state._points_to_evaluate
        self._gs = state._gs
        self._ls = state._ls
        self._resources_per_trial = state._resources_per_trial
        self._mem_size = state._mem_size
        self._mem_threshold = state._mem_threshold

    def restore_from_dir(self, checkpoint_dir: str):
        super.restore_from_dir(checkpoint_dir)

    def on_trial_complete(self, trial_id: str, result: Optional[Dict] = None,
                          error: bool = False):
        ''' search thread updater and cleaner
        '''
        thread_id = self._trial_proposed_by.get(trial_id)
        if thread_id in self._search_thread_pool:
            self._search_thread_pool[thread_id].on_trial_complete(
                trial_id, result, error)
            del self._trial_proposed_by[trial_id]
        if result:
            config = {}
            for key, value in result.items():
                if key.startswith('config/'):
                    config[key[7:]] = value
            if error:  # remove from result cache
                del self._result[self._ls.config_signature(config)]
            else:  # add to result cache
                self._result[self._ls.config_signature(config)] = result
            # update target metric if improved
            if (result[self._metric] - self._metric_target) * self._ls.metric_op < 0:
                self._metric_target = result[self._metric]
            if not thread_id and self._create_condition(result):
                # thread creator
                self._search_thread_pool[self._thread_count] = SearchThread(
                    self._ls.mode,
                    self._ls.create(config, result[self._metric], cost=result[
                        self.cost_attr])
                )
                thread_id = self._thread_count
                self._thread_count += 1
                self._update_admissible_region(
                    config, self._ls_bound_min, self._ls_bound_max)
            # reset admissible region to ls bounding box
            self._gs_admissible_min.update(self._ls_bound_min)
            self._gs_admissible_max.update(self._ls_bound_max)
        # cleaner
        if thread_id and thread_id in self._search_thread_pool:
            # local search thread
            self._clean(thread_id)

    def _update_admissible_region(self, config, admissible_min, admissible_max):
        # update admissible region
        normalized_config = self._ls.normalize(config)
        for key in admissible_min:
            value = normalized_config[key]
            if value > admissible_max[key]:
                admissible_max[key] = value
            elif value < admissible_min[key]:
                admissible_min[key] = value

    def _create_condition(self, result: Dict) -> bool:
        ''' create thread condition
        '''
        if len(self._search_thread_pool) < 2:
            return True
        obj_median = np.median(
            [thread.obj_best1 for id, thread in self._search_thread_pool.items()
             if id])
        return result[self._metric] * self._ls.metric_op < obj_median

    def _clean(self, thread_id: int):
        ''' delete thread and increase admissible region if converged,
        merge local threads if they are close
        '''
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
        if self._search_thread_pool[thread_id].converged:
            todelete.add(thread_id)
            for key in self._ls_bound_max:
                self._ls_bound_max[key] += self._ls.STEPSIZE
                self._ls_bound_min[key] -= self._ls.STEPSIZE
        for id in todelete:
            del self._search_thread_pool[id]

    def _inferior(self, id1: int, id2: int) -> bool:
        ''' whether thread id1 is inferior to id2
        '''
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
        if trial_id not in self._trial_proposed_by:
            return
        thread_id = self._trial_proposed_by[trial_id]
        if thread_id not in self._search_thread_pool:
            return
        self._search_thread_pool[thread_id].on_trial_result(trial_id, result)

    def suggest(self, trial_id: str) -> Optional[Dict]:
        ''' choose thread, suggest a valid config
        '''
        if self._init_used and not self._points_to_evaluate:
            choice, backup = self._select_thread()
            if choice < 0:  # timeout
                return None
            self._use_rs = False
            config = self._search_thread_pool[choice].suggest(trial_id)
            # preliminary check; not checking config validation
            skip = self._should_skip(choice, trial_id, config)
            if skip:
                if choice:
                    return None
                # use rs when BO fails to suggest a config
                self._use_rs = True
                for _, generated in generate_variants({'config': self._ls.space}):
                    config = generated['config']
                    break  # get one random config
                skip = self._should_skip(choice, trial_id, config)
                if skip:
                    return None
            if choice or self._valid(config):
                # LS or valid or no backup choice
                self._trial_proposed_by[trial_id] = choice
            else:  # invalid config proposed by GS
                self._use_rs = False
                if choice == backup:
                    # use CFO's init point
                    init_config = self._ls.init_config
                    config = self._ls.complete_config(
                        init_config, self._ls_bound_min, self._ls_bound_max)
                    self._trial_proposed_by[trial_id] = choice
                else:
                    config = self._search_thread_pool[backup].suggest(trial_id)
                    skip = self._should_skip(backup, trial_id, config)
                    if skip:
                        return None
                    self._trial_proposed_by[trial_id] = backup
                    choice = backup
            if not choice:  # global search
                if self._ls._resource:
                    # TODO: min or median?
                    config[self._ls.prune_attr] = self._ls.min_resource
                # temporarily relax admissible region for parallel proposals
                self._update_admissible_region(
                    config, self._gs_admissible_min, self._gs_admissible_max)
            else:
                self._update_admissible_region(
                    config, self._ls_bound_min, self._ls_bound_max)
                self._gs_admissible_min.update(self._ls_bound_min)
                self._gs_admissible_max.update(self._ls_bound_max)
            self._result[self._ls.config_signature(config)] = {}
        else:  # use init config
            init_config = self._points_to_evaluate.pop(
                0) if self._points_to_evaluate else self._ls.init_config
            config = self._ls.complete_config(
                init_config, self._ls_bound_min, self._ls_bound_max)
            config_signature = self._ls.config_signature(config)
            result = self._result.get(config_signature)
            if result:  # tried before
                return None
            elif result is None:  # not tried before
                self._result[config_signature] = {}
            else:  # running but no result yet
                return None
            self._init_used = True
            self._trial_proposed_by[trial_id] = 0
        return config

    def _should_skip(self, choice, trial_id, config) -> bool:
        ''' if config is None or config's result is known or above mem threshold
            return True; o.w. return False
        '''
        if config is None:
            return True
        config_signature = self._ls.config_signature(config)
        exists = config_signature in self._result
        # check mem constraint
        if not exists and self._mem_threshold and self._mem_size(
                config) > self._mem_threshold:
            self._result[config_signature] = {
                self._metric: np.inf * self._ls.metric_op, 'time_total_s': 1
            }
            exists = True
        if exists:
            if not self._use_rs:
                result = self._result.get(config_signature)
                if result:
                    self._search_thread_pool[choice].on_trial_complete(
                        trial_id, result, error=False)
                    if choice:
                        # local search thread
                        self._clean(choice)
                # else:
                #     # tell the thread there is an error
                #     self._search_thread_pool[choice].on_trial_complete(
                #         trial_id, {}, error=True)
            return True
        return False

    def _select_thread(self) -> Tuple:
        ''' thread selector; use can_suggest to check LS availability
        '''
        # update priority
        min_eci = self._deadline - time.time()
        if min_eci <= 0:
            return -1, -1
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
            # if thread_id:
            #     print(
            #         f"priority of thread {thread_id}={thread.priority}")
            #     logger.debug(
            #         f"thread {thread_id}.can_suggest={thread.can_suggest}")
            if thread_id and thread.can_suggest:
                priority = thread.priority
                if priority > priority1:
                    priority1 = priority
                    top_thread_id = thread_id
                if priority > priority2 or backup_thread_id == 0:
                    priority2 = priority
                    backup_thread_id = thread_id
        return top_thread_id, backup_thread_id

    def _valid(self, config: Dict) -> bool:
        ''' config validator
        '''
        normalized_config = self._ls.normalize(config)
        for key in self._gs_admissible_min:
            if key in config:
                value = normalized_config[key]
                if value + self._ls.STEPSIZE < self._gs_admissible_min[key] \
                        or value > self._gs_admissible_max[key] + self._ls.STEPSIZE:
                    return False
        return True


try:
    from ray.tune import (uniform, quniform, choice, randint, qrandint, randn,
                          qrandn, loguniform, qloguniform)
except ImportError:
    from ..tune.sample import (uniform, quniform, choice, randint, qrandint, randn,
                               qrandn, loguniform, qloguniform)

try:
    from nni.tuner import Tuner as NNITuner
    from nni.utils import extract_scalar_reward

    class BlendSearchTuner(BlendSearch, NNITuner):
        '''Tuner class for NNI
        '''

        def receive_trial_result(self, parameter_id, parameters, value,
                                 **kwargs):
            '''
            Receive trial's final result.
            parameter_id: int
            parameters: object created by 'generate_parameters()'
            value: final metrics of the trial, including default metric
            '''
            result = {}
            for key, value in parameters.items():
                result['config/' + key] = value
            reward = extract_scalar_reward(value)
            result[self._metric] = reward
            # if nni does not report training cost,
            # using sequence as an approximation.
            # if no sequence, using a constant 1
            result[self.cost_attr] = value.get(self.cost_attr, value.get(
                'sequence', 1))
            self.on_trial_complete(str(parameter_id), result)
        ...

        def generate_parameters(self, parameter_id, **kwargs) -> Dict:
            '''
            Returns a set of trial (hyper-)parameters, as a serializable object
            parameter_id: int
            '''
            return self.suggest(str(parameter_id))
        ...

        def update_search_space(self, search_space):
            '''
            Tuners are advised to support updating search space at run-time.
            If a tuner can only set search space once before generating first hyper-parameters,
            it should explicitly document this behaviour.
            search_space: JSON object created by experiment owner
            '''
            config = {}
            for key, value in search_space.items():
                v = value.get("_value")
                _type = value['_type']
                if _type == 'choice':
                    config[key] = choice(v)
                elif _type == 'randint':
                    config[key] = randint(v[0], v[1] - 1)
                elif _type == 'uniform':
                    config[key] = uniform(v[0], v[1])
                elif _type == 'quniform':
                    config[key] = quniform(v[0], v[1], v[2])
                elif _type == 'loguniform':
                    config[key] = loguniform(v[0], v[1])
                elif _type == 'qloguniform':
                    config[key] = qloguniform(v[0], v[1], v[2])
                elif _type == 'normal':
                    config[key] = randn(v[1], v[2])
                elif _type == 'qnormal':
                    config[key] = qrandn(v[1], v[2], v[3])
                else:
                    raise ValueError(
                        f'unsupported type in search_space {_type}')
            self._ls.set_search_properties(None, None, config)
            if self._gs is not None:
                self._gs.set_search_properties(None, None, config)
            self._init_search()

except ImportError:
    class BlendSearchTuner(BlendSearch):
        pass


class CFO(BlendSearchTuner):
    ''' class for CFO algorithm
    '''

    __name__ = 'CFO'

    def suggest(self, trial_id: str) -> Optional[Dict]:
        # Number of threads is 1 or 2. Thread 0 is a vacuous thread
        assert len(self._search_thread_pool) < 3, len(self._search_thread_pool)
        if len(self._search_thread_pool) < 2:
            # When a local converges, the number of threads is 1
            # Need to restart
            self._init_used = False
        return super().suggest(trial_id)

    def _select_thread(self) -> Tuple:
        for key in self._search_thread_pool:
            if key:
                return key, key

    def _create_condition(self, result: Dict) -> bool:
        ''' create thread condition
        '''
        return len(self._search_thread_pool) < 2


def create_next(client):
    ''' functional API for HPO
    '''
    state = client.get_state()
    setting = client.get_settings_dict()
    if state is None:
        # first time call
        try:
            from ray.tune.trial import Trial
        except ImportError:
            from ..tune.trial import Trial
        method = setting.get('method', 'BlendSearch')
        mode = client.get_optimization_mode()
        if mode == 'minimize':
            mode = 'min'
        elif mode == 'maximize':
            mode = 'max'
        metric = client.get_primary_metric()
        hp_space = client.get_hyperparameter_space_dict()
        space = {}
        for key, value in hp_space.items():
            t = value["type"]
            if t == 'continuous':
                space[key] = uniform(value["min_val"], value["max_val"])
            elif t == 'discrete':
                space[key] = choice(value["values"])
            elif t == 'integral':
                space[key] = randint(value["min_val"], value["max_val"])
            elif t == 'quantized_continuous':
                space[key] = quniform(value["min_val"], value["max_val"],
                                      value["step"])
        init_config = setting.get('init_config', None)
        if init_config:
            points_to_evaluate = [init_config]
        else:
            points_to_evaluate = None
        cat_hp_cost = setting.get('cat_hp_cost', None)

        if method == 'BlendSearch':
            Algo = BlendSearch
        elif method == 'CFO':
            Algo = CFO
        algo = Algo(
            mode=mode,
            metric=metric,
            space=space,
            points_to_evaluate=points_to_evaluate,
            cat_hp_cost=cat_hp_cost,
        )
        time_budget_s = setting.get('time_budget_s', None)
        if time_budget_s:
            algo._deadline = time_budget_s + time.time()
        config2trialid = {}
    else:
        algo = state['algo']
        config2trialid = state['config2trialid']
    # update finished trials
    trials_completed = []
    for trial in client.get_trials():
        if trial.end_time is not None:
            signature = algo._ls.config_signature(trial.hp_sample)
            if not algo._result[signature]:
                trials_completed.append((trial.end_time, trial))
    trials_completed.sort()
    for t in trials_completed:
        end_time, trial = t
        trial_id = config2trialid[trial.hp_sample]
        result = {}
        result[algo.metric] = trial.metrics[algo.metric].values[-1]
        result[algo.cost_attr] = (end_time - trial.start_time).total_seconds()
        for key, value in trial.hp_sample.items():
            result['config/' + key] = value
        algo.on_trial_complete(trial_id, result=result)
    # propose new trial
    trial_id = Trial.generate_id()
    config = algo.suggest(trial_id)
    if config:
        config2trialid[config] = trial_id
        client.launch_trial(config)
    client.update_state({'algo': algo, 'config2trialid': config2trialid})
