'''!
 * Copyright (c) 2020-2021 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in the
 * project root for license information.
'''
from typing import Dict, Optional, List, Tuple
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

    cost_attr = "time_total_s" # cost attribute in result

    def __init__(self,
                 metric: Optional[str] = None,
                 mode: Optional[str] = None,
                 space: Optional[dict] = None,
                 points_to_evaluate: Optional[List[Dict]] = None,
                 cat_hp_cost: Optional[dict] = None,
                 prune_attr: Optional[str] = None,
                 min_resource: Optional[float] = None,
                 max_resource: Optional[float] = None,
                 reduction_factor: Optional[float] = None,
                 resources_per_trial: Optional[dict] = None,
                 global_search_alg: Optional[Searcher] = None,
                 mem_size = None):
        '''Constructor

        Args:
            metric: A string of the metric name to optimize for.
                minimization or maximization.
            mode: A string in ['min', 'max'] to specify the objective as
            space: A dictionary to specify the search space.
            points_to_evaluate: Initial parameter suggestions to be run first. 
                The first element needs to be a dictionary from a subset of 
                controlled dimensions to the initial low-cost values. 
                e.g.,
                
                .. code-block:: python
                
                    [{'epochs': 1}]

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
        '''
        self._metric, self._mode = metric, mode
        if points_to_evaluate: init_config = points_to_evaluate[0]
        else: init_config = {}
        self._points_to_evaluate = points_to_evaluate
        if global_search_alg is not None:
            self._gs = global_search_alg
        elif getattr(self, '__name__', None) != 'CFO':
            self._gs = GlobalSearch(space=space, metric=metric, mode=mode)
        else:
            self._gs = None
        self._ls = LocalSearch(init_config, metric, mode, cat_hp_cost, space,
         prune_attr, min_resource, max_resource, reduction_factor)
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
            if metric: self._metric = metric
            if mode: self._mode = mode
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
        self._thread_count = 1 # total # threads created
        self._init_used = self._ls.init_config is None
        self._trial_proposed_by = {} # trial_id: str -> thread_id: int
        self._admissible_min = self._ls.normalize(self._ls.init_config)
        self._admissible_max = self._admissible_min.copy()
        self._result = {} # config_signature: tuple -> result: Dict
        self._deadline = np.inf

    def save(self, checkpoint_path: str):
        save_object = (self._metric_target, self._search_thread_pool,
            self._thread_count, self._init_used, self._trial_proposed_by,
            self._admissible_min, self._admissible_max, self._result,
            self._deadline)
        with open(checkpoint_path, "wb") as outputFile:
            pickle.dump(save_object, outputFile)
            
    def restore(self, checkpoint_path: str):
        with open(checkpoint_path, "rb") as inputFile:
            save_object = pickle.load(inputFile)
        self._metric_target, self._search_thread_pool, \
            self._thread_count, self._init_used, self._trial_proposed_by, \
            self._admissible_min, self._admissible_max, self._result, \
            self._deadline = save_object

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
            # if not thread_id: logger.info(f"result {result}")
        if result:
            config = {}
            for key, value in result.items():
                if key.startswith('config/'):
                    config[key[7:]] = value
            if error: # remove from result cache
                del self._result[self._ls.config_signature(config)]
            else: # add to result cache
                self._result[self._ls.config_signature(config)] = result
            # update target metric if improved
            if (result[self._metric]-self._metric_target)*self._ls.metric_op<0:
                self._metric_target = result[self._metric]
            if thread_id: # from local search
                # update admissible region
                normalized_config = self._ls.normalize(config)
                for key in self._admissible_min:
                    value = normalized_config[key]
                    if value > self._admissible_max[key]:
                        self._admissible_max[key] = value
                    elif value < self._admissible_min[key]:
                        self._admissible_min[key] = value
            elif self._create_condition(result):
                # thread creator
                self._search_thread_pool[self._thread_count] = SearchThread(
                    self._ls.mode,
                    self._ls.create(config, result[self._metric], cost=result[
                        self.cost_attr])
                )
                thread_id = self._thread_count
                self._thread_count += 1
                
        # cleaner
        # logger.info(f"thread {thread_id} in search thread pool="
        #     f"{thread_id in self._search_thread_pool}")
        if thread_id and thread_id in self._search_thread_pool:
            # local search thread
            self._clean(thread_id)

    def _create_condition(self, result: Dict) -> bool:
        ''' create thread condition
        '''
        if len(self._search_thread_pool) < 2: return True
        obj_median = np.median([thread.obj_best1 for id, thread in
         self._search_thread_pool.items() if id])
        return result[self._metric] * self._ls.metric_op < obj_median

    def _clean(self, thread_id: int):
        ''' delete thread and increase admissible region if converged,
        merge local threads if they are close
        '''
        assert thread_id
        todelete = set()
        for id in self._search_thread_pool:
            if id and id!=thread_id:
                if self._inferior(id, thread_id):
                    todelete.add(id)
        for id in self._search_thread_pool:
            if id and id!=thread_id:
                if self._inferior(thread_id, id):
                    todelete.add(thread_id)
                    break        
        # logger.info(f"thead {thread_id}.converged="
        #     f"{self._search_thread_pool[thread_id].converged}")
        if self._search_thread_pool[thread_id].converged:
            todelete.add(thread_id)
            for key in self._admissible_min:
                self._admissible_max[key] += self._ls.STEPSIZE
                self._admissible_min[key] -= self._ls.STEPSIZE            
        for id in todelete:
            del self._search_thread_pool[id]

    def _inferior(self, id1: int, id2: int) -> bool:
        ''' whether thread id1 is inferior to id2
        '''
        t1 = self._search_thread_pool[id1]
        t2 = self._search_thread_pool[id2]
        if t1.obj_best1 < t2.obj_best2: return False
        elif t1.resource and t1.resource < t2.resource: return False
        elif t2.reach(t1): return True
        else: return False

    def on_trial_result(self, trial_id: str, result: Dict):
        if trial_id not in self._trial_proposed_by: return
        thread_id = self._trial_proposed_by[trial_id]
        if not thread_id in self._search_thread_pool: return
        self._search_thread_pool[thread_id].on_trial_result(trial_id, result)

    def suggest(self, trial_id: str) -> Optional[Dict]:
        ''' choose thread, suggest a valid config
        '''
        if self._init_used and not self._points_to_evaluate:
            choice, backup = self._select_thread()
            # logger.debug(f"choice={choice}, backup={backup}")
            if choice < 0: return None # timeout
            self._use_rs = False
            config = self._search_thread_pool[choice].suggest(trial_id)
            skip = self._should_skip(choice, trial_id, config)
            if skip:
                if choice: 
                    # logger.info(f"skipping choice={choice}, config={config}")
                    return None
                # use rs
                self._use_rs = True
                for _, generated in generate_variants(
                    {'config': self._ls.space}):
                    config = generated['config']
                    break
                # logger.debug(f"random config {config}")
                skip = self._should_skip(choice, trial_id, config)
                if skip: return None
            # if not choice: logger.info(config)
            if choice or backup == choice or self._valid(config): 
                # LS or valid or no backup choice
                self._trial_proposed_by[trial_id] = choice
            else: # invalid config proposed by GS
                if not self._use_rs:
                    self._search_thread_pool[choice].on_trial_complete(
                        trial_id, {}, error=True) # tell GS there is an error
                self._use_rs = False
                config = self._search_thread_pool[backup].suggest(trial_id)
                skip = self._should_skip(backup, trial_id, config)
                if skip: 
                    return None
                self._trial_proposed_by[trial_id] = backup
                choice = backup
            # if choice: self._pending.add(choice) # local search thread pending
            if not choice:
                if self._ls._resource: 
                # TODO: add resource to config proposed by GS, min or median?
                    config[self._ls.prune_attr] = self._ls.min_resource
            self._result[self._ls.config_signature(config)] = {}
        else: # use init config
            init_config = self._points_to_evaluate.pop(
                0) if self._points_to_evaluate else self._ls.init_config
            config = self._ls.complete_config(init_config,
             self._admissible_min, self._admissible_max)
                # logger.info(f"reset config to {config}")
            config_signature = self._ls.config_signature(config)
            result = self._result.get(config_signature)
            if result: # tried before
                # self.on_trial_complete(trial_id, result)
                return None
            elif result is None: # not tried before
                self._result[config_signature] = {}
            else: return None # running but no result yet
            self._init_used = True
        # logger.info(f"config={config}")
        return config

    def _should_skip(self, choice, trial_id, config) -> bool:
        ''' if config is None or config's result is known or above mem threshold
            return True; o.w. return False
        '''
        if config is None: return True
        config_signature = self._ls.config_signature(config)
        exists = config_signature in self._result
        # check mem constraint
        if not exists and self._mem_threshold and self._mem_size(
            config)>self._mem_threshold:
            self._result[config_signature] = {
                self._metric:np.inf*self._ls.metric_op, 'time_total_s':1}
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
                else:
                    # tell the thread there is an error
                    self._search_thread_pool[choice].on_trial_complete(
                        trial_id, {}, error=True) 
            return True
        return False

    def _select_thread(self) -> Tuple:
        ''' thread selector; use can_suggest to check LS availability
        '''
        # update priority
        min_eci = self._deadline - time.time()
        if min_eci <= 0: return -1, -1
        max_speed = 0
        for thread in self._search_thread_pool.values():            
            if thread.speed > max_speed: max_speed = thread.speed
        for thread in self._search_thread_pool.values():            
            thread.update_eci(self._metric_target, max_speed)
            if thread.eci < min_eci: min_eci = thread.eci
        for thread in self._search_thread_pool.values():
            thread.update_priority(min_eci)

        top_thread_id = backup_thread_id = 0
        priority1 = priority2 = self._search_thread_pool[0].priority
        # logger.debug(f"priority of thread 0={priority1}")
        for thread_id, thread in self._search_thread_pool.items():
            # if thread_id:
            #     logger.debug(
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
        for key in self._admissible_min:
            if key in config:
                value = config[key]
                # logger.info(
                #     f"{key},{value},{self._admissible_min[key]},{self._admissible_max[key]}")
                if value<self._admissible_min[
                    key] or value>self._admissible_max[key]:
                    return False
        return True


try:
    from nni.tuner import Tuner as NNITuner
    from nni.utils import extract_scalar_reward
    try:
        from ray.tune import (uniform, quniform, choice, randint, qrandint, randn,
    qrandn, loguniform, qloguniform)
    except:
        from .sample import (uniform, quniform, choice, randint, qrandint, randn,
    qrandn, loguniform, qloguniform)

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
            for key, value in parameters:
                result['config/'+key] = value
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
            for key, value in search_space:
                v = value.get("_value")
                _type = value['_type']
                if _type == 'choice':
                    config[key] = choice(v)
                elif _type == 'randint':
                    config[key] = randint(v[0], v[1]-1)
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

except:
    class BlendSearchTuner(BlendSearch): pass


class CFO(BlendSearchTuner):
    ''' class for CFO algorithm
    '''

    __name__ = 'CFO'

    def suggest(self, trial_id: str) -> Optional[Dict]:
        # Number of threads is 1 or 2. Thread 0 is a vacuous thread
        assert len(self._search_thread_pool)<3, len(self._search_thread_pool)
        if len(self._search_thread_pool) < 2:
            # When a local converges, the number of threads is 1
            # Need to restart
            self._init_used = False
        return super().suggest(trial_id)

    def _select_thread(self) -> Tuple:
        for key in self._search_thread_pool:
            if key: return key, key

    def _create_condition(self, result: Dict) -> bool:
        ''' create thread condition
        '''
        return len(self._search_thread_pool) < 2


