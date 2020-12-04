'''!
 * Copyright (c) 2020 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. 
'''

from functools import partial
from .ml import train_estimator
import time
import math
import numpy as np
from .space import config_space, estimator_size, get_config_values, \
    generate_config_ini, generate_config_max, generate_config_min
from .config import SPLIT_RATIO, MIN_SAMPLE_TRAIN, \
    HISTORY_SIZE, MEM_THRES, BASE_Const, BASE_LOWER_BOUND
from random import gauss


def rand_vector_unit_sphere(dims):
    vec = [gauss(0, 1) for i in range(dims)]
    mag = sum(x**2 for x in vec) ** .5
    return [x / mag for x in vec]


def rand_vector_gaussian(dims):
    vec = [gauss(0, 1) for i in range(dims)]
    return vec


class ParamSearch:
    '''
    the class for searching params for 1 learner
    '''

    def __init__(self, estimator, data_size,
                 compute_with_config, train_with_config, save_info_helper=None,
                 init_sample_size=MIN_SAMPLE_TRAIN, objective_name='regression',
                 log_type='better', config_space_info=None, size_estimator=None,
                 split_ratio=SPLIT_RATIO, base_change='sqrtK', use_dual_dir=True,
                 move_type='geo'):
        self.log_type = log_type
        self.base_change = base_change
        if init_sample_size > data_size:
            init_sample_size = data_size
        self.next_sample_size = {}
        self.prev_sample_size = {}
        s = init_sample_size
        self.prev_sample_size[s] = s
        self.estimator_configspace = config_space_info or config_space(
            estimator, data_size, objective_name)
        self.get_size_for_config = size_estimator or (
            lambda x: estimator_size(x, estimator))
        config_min_dic_primary, config_min_dic_more, config_min_dic = \
            generate_config_min(estimator, self.estimator_configspace, None)
        self.min_config_primary = np.array(
            list(config_min_dic_primary.values()))
        self.min_config_more = np.array(list(config_min_dic_more.values()))
        self.min_config = np.array(list(config_min_dic.values()))
        # init configurations for different sample size
        config_init_dic_primary, config_init_dic_more, _, config_type_dic = \
            generate_config_ini(estimator, self.estimator_configspace)
        self.init_config_dic_primary = {s: config_init_dic_primary}
        self.init_config_dic_more = {s: config_init_dic_more}
        self.init_config_dic_type_dic = {'primary': {
            s: config_init_dic_primary}, 'more': {s: config_init_dic_more}}
        self.init_config_dic = {
            **self.init_config_dic_type_dic['primary'],
            **self.init_config_dic_type_dic['more']
        }
        self.config_type_dic = config_type_dic
        # max configurations for different sample size
        config_max_dic_primary, config_max_dic_more, config_max_dic = \
            generate_config_max(
                estimator, self.estimator_configspace, int(s))
        self.max_config_dic_primary = {s: np.array(
            list(config_max_dic_primary.values()))}
        self.max_config_dic_more = {s: np.array(
            list(config_max_dic_more.values()))}
        self.max_config_dic = {s: np.array(list(config_max_dic.values()))}
        self.dims = (len(self.min_config_primary), len(self.min_config_more))
        # print(self.dims)
        if self.dims[1] > 0 and self.dims[0] > 0:
            self.base_upper_bound = {
                s:
                max(
                    max(
                        (self.max_config_dic_primary[s][i] / self.min_config_primary[i])
                        ** math.sqrt(self.dims[0]) for i in range(self.dims[0])
                    ),
                    max(
                        (self.max_config_dic_more[s][i] / self.min_config_more[i])
                        ** math.sqrt(self.dims[1]) for i in range(self.dims[1]))
                )
            }
        elif self.dims[0] > 0:
            self.base_upper_bound = {
                s:
                max(
                    (self.max_config_dic_primary[s][i] / self.min_config_primary[i])
                    ** (math.sqrt(self.dims[0])) for i in range(self.dims[0])
                )
            }
        else:
            self.base_upper_bound = {
                s:
                max(
                    (self.max_config_dic_more[s][i] / self.min_config_more[i])
                    ** (math.sqrt(self.dims[1])) for i in range(self.dims[1])
                )
            }

        # create sample size sequence
        while s < data_size:
            s2 = self.next_sample_size[s] = s * 2 if s * 2 <= data_size else data_size
            self.prev_sample_size[s2] = s
            s = s2

            config_max_dic_primary, config_max_dic_more, config_max_dic = \
                generate_config_max(
                    estimator, self.estimator_configspace, int(s))
            self.max_config_dic_primary[s] = np.array(
                list(config_max_dic_primary.values()))
            self.max_config_dic_more[s] = np.array(
                list(config_max_dic_more.values()))
            self.max_config_dic[s] = np.array(list(config_max_dic.values()))
            if self.dims[1] > 0 and self.dims[0] > 0:
                self.base_upper_bound[s] = max(
                    max(
                        (self.max_config_dic_primary[s][i]
                         / self.min_config_primary[i])
                        ** math.sqrt(self.dims[0]) for i in range(self.dims[0])
                    ),
                    max(
                        (self.max_config_dic_more[s][i]
                         / self.min_config_more[i])
                        ** math.sqrt(self.dims[1]) for i in range(self.dims[1])
                    )
                )
            elif self.dims[0] > 0:
                self.base_upper_bound[s] = max(
                    (self.max_config_dic_primary[s][i]
                     / self.min_config_primary[i])
                    ** math.sqrt(self.dims[0]) for i in range(self.dims[0])
                )
            else:
                self.base_upper_bound[s] = max(
                    (self.max_config_dic_more[s][i] / self.min_config_more[i])
                    ** math.sqrt(self.dims[1]) for i in range(self.dims[1])
                )

        self.init_sample_size = init_sample_size
        self.data_size = data_size
        self.sample_size_full = int(self.data_size / (1.0 - split_ratio))

        self.compute_with_config = compute_with_config
        self.estimator = estimator

        # for logging
        self.save_helper = save_info_helper
        self.estimator_type_list = ['primary', 'more']
        self.dim = self.dims[0] if self.dims[0] > 0 else self.dims[1]
        self.b = BASE_Const**(math.sqrt(self.dim))
        self.base_ini = self.b
        self.total_dim = sum(self.dims)

        self.epo = 2**(self.dim - 1)
        # keys are [sample size, config], values are (loss, train_time)
        self.config_tried = {}
        self.train_with_config = train_with_config

        self.current_config_loss = None
        self.use_dual_dir = use_dual_dir
        self.move_type = move_type

    def evaluate_config(self, config, sample_size, move='_pos'):
        '''
        evaluate a configuration, update search state, 
        and return whether the state is changed
        '''
        if self.time_from_start >= self.time_budget or move != '_ini' and \
                self.train_time > self.time_budget - self.time_from_start:
            return False

        model, val_loss, new_train_time, from_history, train_loss = \
            self.evaluate_proposed_config(config, sample_size, move)
        # update current config
        self.update_current_config(config, val_loss, sample_size)
        # update best model statistics, including statistics about loss and time
        improved = self.update_search_state_best(
            config, sample_size, model, val_loss, new_train_time, from_history)
        self.time_from_start = time.time() - self.start_time
        if self.save_helper is not None:
            if from_history:
                move = move + '_from_hist'
            self.save_helper.append(self.model_count,
                                    train_loss,
                                    new_train_time,
                                    self.time_from_start,
                                    val_loss,
                                    config,
                                    self.best_loss,
                                    self.best_config[0],
                                    self.estimator,
                                    sample_size)
        return improved

    def get_hist_config_sig(self, sample_size, config):
        config_values = get_config_values(config, self.config_type_dic)
        config_sig = str(sample_size) + '_' + str(config_values)
        return config_sig

    def evaluate_proposed_config(self, config, sample_size, move):
        self.model_count += 1
        config_sig = self.get_hist_config_sig(sample_size, config)
        d = self.total_dim
        history_size_per_d = len(self.config_tried) / float(d)
        if config_sig in self.config_tried:
            val_loss, new_train_time = self.config_tried[config_sig]
            # print(config_sig,'found in history')
            model = train_loss = None
            from_history = True
        else:
            model, val_loss, train_loss, new_train_time, _ = \
                self.compute_with_config(self.estimator, config, sample_size)
            from_history = False
            if history_size_per_d < HISTORY_SIZE:
                self.config_tried[config_sig] = (val_loss, new_train_time)

        if self.first_move:
            self.init_config_dic[sample_size] = config
            move = '_ini'
            self.base = self.base_ini
            self.num_noimprovement = 0
        move = str(self.estimator) + move
        return model, val_loss, new_train_time, from_history, train_loss

    def update_current_config(self, config, val_loss, sample_size):
        if self.first_move or val_loss < self.current_config_loss:
            self.first_move = False
            # update current config and coressponding sample_size
            self.sample_size = sample_size
            self.config = config
            self.config_primary = {x: config[x]
                                   for x in self.config_primary.keys()}
            try:
                self.config_more = {x: config[x]
                                    for x in self.config_more.keys()}
            except:
                self.config_more = {}
            self.current_config_loss = val_loss

    def update_reset_best_config_loss(self, sample_size, config, val_loss):
        if sample_size == self.data_size:
            if self.best_config_loss_dic_full_reset[1] is None:
                self.best_config_loss_dic_full_reset = [
                    config, val_loss, self.model_count]
            else:
                full_reset_best_loss = self.best_config_loss_dic_full_reset[1]
                if val_loss < full_reset_best_loss:
                    self.best_config_loss_dic_full_reset = [
                        config, full_reset_best_loss, self.model_count]

    def update_search_state_best(self, config, sample_size, model, val_loss,
                                 new_train_time, from_history):
        # upate the loss statistics for a particular sample size
        if sample_size not in self.best_config_loss_samplesize_dic:
            self.best_config_loss_samplesize_dic[sample_size] = [
                config, val_loss, self.model_count]
        else:
            s_best_loss = self.best_config_loss_samplesize_dic[sample_size][1]
            if val_loss < s_best_loss:
                self.best_config_loss_samplesize_dic[sample_size] = [
                    config, val_loss, self.model_count]

        self.update_reset_best_config_loss(sample_size, config, val_loss)

        # update best model statistics, including statistics about loss and time
        if val_loss < self.new_loss:
            self.old_loss = self.new_loss if self.new_loss < float(
                'inf') else 2 * val_loss
            self.new_loss = val_loss
            self.old_loss_time = self.new_loss_time
            self.old_train_time = self.train_time
            self.new_loss_time = self.train_time = new_train_time
            if val_loss < self.best_loss:
                self.best_config = [self.config, self.model_count]
                if not from_history:
                    self.trained_estimator = model
                    # print(model)
                else:
                    print(val_loss, self.best_loss)
                self.best_loss = val_loss
                self.time_best_found = self.time_from_start
            return True
        else:
            if not from_history:
                self.new_loss_time += new_train_time
            return False

    def get_proposal(self, current_config, rand_vector_func, base, move_type):
        rand_vector = rand_vector_func(len(current_config))
        rand_vector = [i for i in rand_vector]
        rand_vector_neg = [-i for i in rand_vector]

        move_vector = {}
        move_vector_neg = {}

        index_ = 0
        for k, v in current_config.items():
            if 'geo' in move_type:
                # get the move vector using the proposed random vector
                move_vector[k] = v * (base**(rand_vector[index_]))
                move_vector_neg[k] = v * (base**(rand_vector_neg[index_]))
            else:
                move_vector[k] = v + (base * (rand_vector[index_]))
                move_vector_neg[k] = v + (base * (rand_vector_neg[index_]))
            index_ += 1

        # as long as one of the proposed model (+ or -) is within the mem_limit
        # we will proceed
        if not self.use_dual_dir:
            move_vector_neg = None
        return move_vector, move_vector_neg

    def get_config_from_move_vector(self, v, estimator_type):
        if v != None:
            if 'all' in estimator_type:
                v = v
            elif 'primary' in estimator_type:
                v = {**v, **self.config_more}
            else:
                v = {**self.config_primary, **v}

            bounded_v = self.get_v_within_min_max(v)
        else:
            bounded_v = None
        return bounded_v

    def dual_direction_sample(self, base, current_search_config,
                              estimator_type='primary', rand_vector_func=rand_vector_unit_sphere,
                              mem_thres=MEM_THRES, move_type='geo'):
        current_config = current_search_config
        if len(current_config) == 0:
            return None, None
        bounded_v_list = [None, None]
        while not bounded_v_list[0] and not bounded_v_list[
                1] and self.time_from_start < self.time_budget:
            move_vector, move_vector_neg = self.get_proposal(
                current_config, rand_vector_func,
                base, move_type)
            bounded_v_list = [move_vector, move_vector_neg]
            for i, v in enumerate(bounded_v_list):
                bounded_v = self.get_config_from_move_vector(v, estimator_type)
                proposed_model_size = self.get_size_for_config(bounded_v)
                proposed_model_size = 0 if not isinstance(
                    proposed_model_size, float) else proposed_model_size
                if proposed_model_size > mem_thres:
                    # print(bounded_v, proposed_model_size, mem_thres)
                    bounded_v = None
                bounded_v_list[i] = bounded_v
            self.time_from_start = time.time() - self.start_time
        return bounded_v_list

    def get_v_within_min_max(self, v):
        index_ = 0
        bounded_v = {}
        for key, value in v.items():
            new_value = min(max(
                value, self.min_config[index_]), self.max_config_dic[
                    self.sample_size][index_])
            bounded_v[key] = new_value
            index_ += 1
        return bounded_v

    def expected_time_improvement_search(self):
        return max(self.old_loss_time - self.old_train_time + self.train_time,
                   self.new_loss_time)

    def increase_sample_size(self):
        '''
        whether it's time to increase sample size
        '''
        expected_time_improvement_sample = 2 * self.train_time
        self.increase = self.sample_size < self.data_size and (
            self.estimator_type == 0 or self.dims[0] == 0) and (
                not self.improved
            or expected_time_improvement_sample
            < self.expected_time_improvement_search()
        )
        return self.increase

    def search_begin(self, time_budget, start_time=None):
        self.time_budget = time_budget
        if not start_time:
            self.start_time = time.time()
        else:
            self.start_time = start_time
        # the time to train the last selected config
        self.old_train_time = self.train_time = 0
        self.time_from_start = 0
        # search states
        self.first_move = True
        self.improved = True
        self.estimator_type = 0 if self.dims[0] > 0 else 1

        self.old_loss = self.new_loss = self.best_loss = float('+inf')
        # new_loss_time is the time from the beginning of training self.config to
        # now,
        # old_loss_time is the time from the beginning of training the old
        # self.config to the beginning of training self.config
        self.old_loss_time = self.new_loss_time = 0

        self.trained_estimator = None
        self.model_count = 0
        self.K = 0
        self.old_modelcount = 0

        # self.config has two parts: config_primary contain the configs
        # that are related with model complexity, config_more contains the
        # configs that is not related with model complexity
        self.config_primary = self.init_config_dic_primary[self.init_sample_size]
        self.config_more = self.init_config_dic_more[self.init_sample_size]
        self.config = {**self.config_primary, **self.config_more}
        self.best_config = [None, None]
        # key: sample size, value: [best_config, best_loss, model_count] under
        # sample size in the key
        self.best_config_loss_samplesize_dic = {
            self.init_sample_size: [self.config, self.old_loss, self.model_count]}
        # key: sample size, value: [best_config, best_loss, model_count] under
        # sample size in the key
        self.best_config_loss_dic_full_reset = [None, None, None]
        self.sample_size = self.init_sample_size
        self.base_change_bound = 1
        self.base_change_count = 0
        self.evaluate_config(self.config, self.sample_size, '_ini')
        self.increase = False

    def train_config(self, config, sample_size):
        '''
        train a configuration
        '''
        # print('Evalute Config')
        if self.time_from_start >= self.time_budget:
            return False
        config_sig = self.get_hist_config_sig(sample_size, config)
        if not config_sig in self.config_tried:
            _, new_train_time = self.train_with_config(
                self.estimator, config, sample_size)
            train_loss, val_loss, move = None, self.new_loss, str(
                self.estimator) + '_trainAll'
            self.time_from_start = time.time() - self.start_time
            if self.save_helper is not None:
                self.save_helper.append(self.model_count,
                                        train_loss,
                                        new_train_time,
                                        self.time_from_start,
                                        val_loss,
                                        config,
                                        self.best_loss,
                                        self.best_config,
                                        move,
                                        sample_size)
            self.config_tried[config_sig] = (val_loss, new_train_time)

    def try_increase_sample_size(self):
        # print( self.estimator, self.sample_size)
        if self.sample_size in self.next_sample_size:
            if self.increase_sample_size():
                self.first_move = True
                self.improved = True
                self.estimator_type = 0 if self.dims[0] > 0 else 1
                self.evaluate_config(
                    self.config, self.next_sample_size[self.sample_size])
        if not self.old_modelcount and self.sample_size == self.data_size:
            self.old_modelcount = self.model_count

    def setup_current_search_config(self):
        estimator_type = self.estimator_type_list[self.estimator_type]
        if 'all' in estimator_type:
            current_search_config = self.config
        elif 'primary' in estimator_type:
            current_search_config = self.config_primary
        else:
            current_search_config = self.config_more
            # print(self.config_more)
        return estimator_type, current_search_config

    def search1step(self, global_best_loss=float('+inf'),
                    retrain_full=True, mem_thres=MEM_THRES, reset_type='init_gaussian'):
        # try to increase sample size
        self.try_increase_sample_size()
        # decide current_search_config according to estimator_type
        estimator_type, current_search_config = \
            self.setup_current_search_config()
        time_left = self.time_budget - self.time_from_start
        if time_left < self.train_time:
            return False
        if retrain_full and self.train_time < time_left < 2 * self.train_time \
                and self.best_loss <= global_best_loss:
            self.train_config(self.best_config[0], self.sample_size_full)

        move_vector, move_vector_neg = self.dual_direction_sample(
            self.base, current_search_config, estimator_type,
            rand_vector_unit_sphere, mem_thres, self.move_type)
        if move_vector is None:
            if move_vector_neg is None:
                self.improved = False
            else:
                self.improved = self.evaluate_config(
                    move_vector_neg, self.sample_size, '_neg' + str(
                        estimator_type))
        else:
            self.improved = self.evaluate_config(
                move_vector, self.sample_size, '_pos' + str(estimator_type))
            if not self.improved:
                if move_vector_neg is None:
                    pass
                else:
                    self.improved = self.evaluate_config(
                        move_vector_neg, self.sample_size, '_neg' + str(
                            estimator_type))
        self.update_noimprovement_stat(
            global_best_loss, retrain_full, reset_type)
        return self.improved

    def update_noimprovement_stat(self, global_best_loss, retrain_full,
                                  reset_type):
        if self.improved:
            self.num_noimprovement = 0
        else:
            self.estimator_type = 1 - self.estimator_type
            if self.dims[self.estimator_type] == 0:
                self.estimator_type = 1 - self.estimator_type
            if self.estimator_type == 1 or self.dims[1] == 0:
                self.noimprovement(global_best_loss, retrain_full, reset_type)

    def noimprovement(self, global_best_loss, retrain_full, reset_type='org'):
        if self.sample_size == self.data_size:
            # Do not wait until full sample size to update num_noimprovement?
            self.num_noimprovement += 1
            if self.num_noimprovement >= self.epo:
                self.num_noimprovement = 0
                # print(self.num_noimprovement, self.epo)
                if self.base_change == 'squareroot':
                    self.base = math.sqrt(self.base)
                else:
                    if self.K == 0:  # first time
                        oldK = self.best_config_loss_dic_full_reset[2] - \
                            self.old_modelcount
                    else:
                        oldK = self.K
                    self.K = self.model_count + 1 - self.old_modelcount
                    if self.base_change == 'K':
                        self.base **= oldK / self.K
                    else:
                        self.base **= math.sqrt(oldK / self.K)
                if self.dims[1] > 0 and self.dims[0] > 0:
                    base_lower_bound = min(
                        min(
                            (1.0 + self.estimator_configspace[i].min_change
                             / self.config_primary[i])
                            ** math.sqrt(self.dims[0])
                            for i in self.config_primary.keys()
                        ),
                        min(
                            (1.0 + self.estimator_configspace[i].min_change
                             / self.config_more[i])
                            ** math.sqrt(self.dims[1])
                            for i in self.config_more.keys()
                        )
                    )
                elif self.dims[0] > 0:
                    base_lower_bound = min(
                        (1.0 + self.estimator_configspace[i].min_change
                         / self.config_primary[i])
                        ** math.sqrt(self.dims[0])
                        for i in self.config_primary.keys()
                    )
                else:
                    base_lower_bound = min(
                        (1.0 + self.estimator_configspace[i].min_change
                         / self.config_more[i])
                        ** math.sqrt(self.dims[1])
                        for i in self.config_more.keys()
                    )
                if np.isinf(base_lower_bound):
                    base_lower_bound = BASE_LOWER_BOUND
                self.base_change_count += 1
                if self.base <= base_lower_bound or \
                        self.base_change_count == self.base_change_bound:
                    if retrain_full and self.sample_size == self.data_size:
                        if self.best_loss <= global_best_loss:
                            # Only train on full data when the curent estimator
                            #  is the best estimator
                            # print('best estimator and train on full data')
                            self.train_config(
                                self.best_config[0], self.sample_size_full)
                    # remaining time is more than enough for another trial
                    if self.time_budget - self.time_from_start > self.train_time:
                        self.base_change_bound <<= 1
                        self.base_change_count = 0
                        self.K = 0
                        self.old_modelcount = self.model_count
                        self.best_config_loss_dic_full_reset = [None, None,
                                                                None]
                        self.first_move = True
                        self.improved = True
                        self.base_ini = min(
                            self.base_ini * 2, self.base_upper_bound[
                                self.sample_size])
                        self.estimator_type = 0 if self.dims[0] > 0 else 1
                        reset_config, reset_sample_size = self.get_reset_config(
                            self.init_sample_size, reset_type)
                        self.sample_size = reset_sample_size
                        # print('reset sample size', reset_sample_size)
                        self.evaluate_config(reset_config, self.sample_size,
                                             '_ini')

    def get_reset_config(self, sample_size, reset_type):
        init_config = self.init_config_dic[self.sample_size]
        reset_sample_size = sample_size
        if 'org' in reset_type:
            reset_config = init_config
        else:
            if 'init_gaussian' in reset_type:
                reset_config = init_config
                reset_sample_size = self.get_reset_sample_size(reset_config)
                config_values = get_config_values(
                    reset_config, self.config_type_dic)
                config_sig = str(reset_sample_size) + '_' + str(config_values)
                count = 0
                while config_sig in self.config_tried and \
                        self.time_from_start < self.time_budget and count < 1000:
                    # TODO: check exhaustiveness? use time as condition?
                    count += 1
                    move, move_neg = self.dual_direction_sample(
                        base=self.b, current_search_config=init_config,
                        estimator_type='all',
                        rand_vector_func=rand_vector_gaussian,
                        move_type=self.move_type)
                    if move:
                        reset_config = move_neg
                    elif move_neg:
                        reset_config = move_neg
                    else:
                        continue
                    reset_sample_size = self.get_reset_sample_size(
                        reset_config)
                    config_values = get_config_values(
                        reset_config, self.config_type_dic)
                    config_sig = str(reset_sample_size) + \
                        '_' + str(config_values)
                    self.time_from_start = time.time() - self.start_time
            else:
                raise NotImplementedError
        return reset_config, reset_sample_size

    def get_reset_sample_size(self, reset_config):
        if not reset_config:
            print('reset_config is none')
        reset_config_size = self.get_size_for_config(reset_config)

        candidate_sample_size_list = []
        for sample_size, config_and_bestloss in \
                self.best_config_loss_samplesize_dic.items():
            s_best_config = config_and_bestloss[0]
            if not s_best_config:
                print('best config is none', sample_size)
            s_best_config_model_size = self.get_size_for_config(s_best_config)
            if s_best_config_model_size >= reset_config_size:
                candidate_sample_size_list.append(sample_size)

        if len(candidate_sample_size_list) != 0:
            return min(candidate_sample_size_list)
        else:
            return self.data_size
