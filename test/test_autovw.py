import unittest

import numpy as np
import scipy.sparse

import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error
import logging
from flaml.tune import loguniform, polynomial_expansion_set
from vowpalwabbit import pyvw
from flaml import AutoVW
import string
import os
import openml

VW_DS_DIR = 'test/data/'
NS_LIST = list(string.ascii_lowercase) + list(string.ascii_uppercase)
logger = logging.getLogger(__name__)


def oml_to_vw_w_grouping(X, y, ds_dir, fname, orginal_dim, group_num,
                         grouping_method='sequential'):
    # split all_indexes into # group_num of groups
    max_size_per_group = int(np.ceil(orginal_dim / float(group_num)))
    # sequential grouping
    if grouping_method == 'sequential':
        group_indexes = []  # lists of lists
        for i in range(group_num):
            indexes = [ind for ind in range(i * max_size_per_group,
                       min((i + 1) * max_size_per_group, orginal_dim))]
            if len(indexes) > 0:
                group_indexes.append(indexes)
        print(group_indexes)
    else:
        NotImplementedError
    if group_indexes:
        if not os.path.exists(ds_dir):
            os.makedirs(ds_dir)
        with open(os.path.join(ds_dir, fname), 'w') as f:
            if isinstance(X, pd.DataFrame):
                raise NotImplementedError
            elif isinstance(X, np.ndarray):
                for i in range(len(X)):
                    NS_content = []
                    for zz in range(len(group_indexes)):
                        ns_features = ' '.join('{}:{:.6f}'.format(ind, X[i][ind]
                                                                  ) for ind in group_indexes[zz])
                        NS_content.append(ns_features)
                    ns_line = '{} |{}'.format(str(y[i]), '|'.join(
                                              '{} {}'.format(NS_LIST[j], NS_content[j]
                                                             ) for j in range(len(group_indexes))))
                    f.write(ns_line)
                    f.write('\n')
            elif isinstance(X, scipy.sparse.csr_matrix):
                print('NotImplementedError for sparse data')
                NotImplementedError


def save_vw_dataset_w_ns(X, y, did, ds_dir, max_ns_num, is_regression):
    """ convert openml dataset to vw example and save to file
    """
    print('is_regression', is_regression)
    if is_regression:
        fname = 'ds_{}_{}_{}.vw'.format(did, max_ns_num, 0)
        print('dataset size', X.shape[0], X.shape[1])
        print('saving data', did, ds_dir, fname)
        dim = X.shape[1]
        oml_to_vw_w_grouping(X, y, ds_dir, fname, dim, group_num=max_ns_num)
    else:
        NotImplementedError


def shuffle_data(X, y, seed):
    try:
        n = len(X)
    except ValueError:
        n = X.getnnz()

    perm = np.random.RandomState(seed=seed).permutation(n)
    X_shuf = X[perm, :]
    y_shuf = y[perm]
    return X_shuf, y_shuf


def get_oml_to_vw(did, max_ns_num, ds_dir=VW_DS_DIR):
    success = False
    print('-----getting oml dataset-------', did)
    ds = openml.datasets.get_dataset(did)
    target_attribute = ds.default_target_attribute
    # if target_attribute is None and did in OML_target_attribute_dict:
    #     target_attribute = OML_target_attribute_dict[did]

    print('target=ds.default_target_attribute', target_attribute)
    data = ds.get_data(target=target_attribute, dataset_format='array')
    X, y = data[0], data[1]  # return X: pd DataFrame, y: pd series
    import scipy
    if scipy.sparse.issparse(X):
        X = scipy.sparse.csr_matrix.toarray(X)
        print('is sparse matrix')
    if data and isinstance(X, np.ndarray):
        print('-----converting oml to vw and and saving oml dataset-------')
        save_vw_dataset_w_ns(X, y, did, ds_dir, max_ns_num, is_regression=True)
        success = True
    else:
        print('---failed to convert/save oml dataset to vw!!!----')
    try:
        X, y = data[0], data[1]  # return X: pd DataFrame, y: pd series
        if data and isinstance(X, np.ndarray):
            print('-----converting oml to vw and and saving oml dataset-------')
            save_vw_dataset_w_ns(X, y, did, ds_dir, max_ns_num, is_regression=True)
            success = True
        else:
            print('---failed to convert/save oml dataset to vw!!!----')
    except ValueError:
        print('-------------failed to get oml dataset!!!', did)
    return success


def load_vw_dataset(did, ds_dir, is_regression, max_ns_num):
    import os
    if is_regression:
        # the second field specifies the largest number of namespaces using.
        fname = 'ds_{}_{}_{}.vw'.format(did, max_ns_num, 0)
        vw_dataset_file = os.path.join(ds_dir, fname)
        # if file does not exist, generate and save the datasets
        if not os.path.exists(vw_dataset_file) or os.stat(vw_dataset_file).st_size < 1000:
            get_oml_to_vw(did, max_ns_num)
        print(ds_dir, vw_dataset_file)
        if not os.path.exists(ds_dir):
            os.makedirs(ds_dir)
        with open(os.path.join(ds_dir, fname), 'r') as f:
            vw_content = f.read().splitlines()
            print(type(vw_content), len(vw_content))
        return vw_content


def get_data(iter_num=None, dataset_id=None, vw_format=True,
             max_ns_num=10, shuffle=False, use_log=True, dataset_type='regression'):
    logging.info('generating data')
    LOG_TRANSFORMATION_THRESHOLD = 100
    # get data from simulation
    import random
    vw_examples = None
    data_id = int(dataset_id)
    # loading oml dataset
    # data = OpenML2VWData(data_id, max_ns_num, dataset_type)
    # Y = data.Y
    if vw_format:
        # vw_examples = data.vw_examples
        vw_examples = load_vw_dataset(did=data_id, ds_dir=VW_DS_DIR, is_regression=True,
                                      max_ns_num=max_ns_num)
        Y = []
        for i, e in enumerate(vw_examples):
            Y.append(float(e.split('|')[0]))
    logger.debug('first data %s', vw_examples[0])
    # do data shuffling or log transformation for oml data when needed
    if shuffle:
        random.seed(54321)
        random.shuffle(vw_examples)

    # do log transformation
    unique_y = set(Y)
    min_y = min(unique_y)
    max_y = max(unique_y)
    if use_log and max((max_y - min_y), max_y) >= LOG_TRANSFORMATION_THRESHOLD:
        log_vw_examples = []
        for v in vw_examples:
            org_y = v.split('|')[0]
            y = float(v.split('|')[0])
            # shift y to ensure all y are positive
            if min_y <= 0:
                y = y + abs(min_y) + 1
            log_y = np.log(y)
            log_vw = v.replace(org_y + '|', str(log_y) + ' |')
            log_vw_examples.append(log_vw)
        logger.info('log_vw_examples %s', log_vw_examples[0:2])
        if log_vw_examples:
            return log_vw_examples
    return vw_examples, Y


class VowpalWabbitNamesspaceTuningProblem:

    def __init__(self, max_iter_num, dataset_id, ns_num, **kwargs):
        use_log = kwargs.get('use_log', True),
        shuffle = kwargs.get('shuffle', False)
        vw_format = kwargs.get('vw_format', True)
        print('dataset_id', dataset_id)
        self.vw_examples, self.Y = get_data(max_iter_num, dataset_id=dataset_id,
                                            vw_format=vw_format, max_ns_num=ns_num,
                                            shuffle=shuffle, use_log=use_log
                                            )
        self.max_iter_num = min(max_iter_num, len(self.Y))
        self._problem_info = {'max_iter_num': self.max_iter_num,
                              'dataset_id': dataset_id,
                              'ns_num': ns_num,
                              }
        self._problem_info.update(kwargs)
        self._fixed_hp_config = kwargs.get('fixed_hp_config', {})
        self.namespace_feature_dim = AutoVW.get_ns_feature_dim_from_vw_example(self.vw_examples[0])
        self._raw_namespaces = list(self.namespace_feature_dim.keys())
        self._setup_search()

    def _setup_search(self):
        self._search_space = self._fixed_hp_config.copy()
        self._init_config = self._fixed_hp_config.copy()
        search_space = {'interactions':
                        polynomial_expansion_set(
                            init_monomials=set(self._raw_namespaces),
                            highest_poly_order=len(self._raw_namespaces),
                            allow_self_inter=False),
                        }
        init_config = {'interactions': set()}
        self._search_space.update(search_space)
        self._init_config.update(init_config)
        logger.info('search space %s %s %s', self._search_space, self._init_config, self._fixed_hp_config)

    @property
    def init_config(self):
        return self._init_config

    @property
    def search_space(self):
        return self._search_space


class VowpalWabbitNamesspaceLRTuningProblem(VowpalWabbitNamesspaceTuningProblem):

    def __init__(self, max_iter_num, dataset_id, ns_num, **kwargs):
        super().__init__(max_iter_num, dataset_id, ns_num, **kwargs)
        self._setup_search()

    def _setup_search(self):
        self._search_space = self._fixed_hp_config.copy()
        self._init_config = self._fixed_hp_config.copy()
        search_space = {'interactions':
                        polynomial_expansion_set(
                            init_monomials=set(self._raw_namespaces),
                            highest_poly_order=len(self._raw_namespaces),
                            allow_self_inter=False),
                        'learning_rate': loguniform(lower=2e-10, upper=1.0)
                        }
        init_config = {'interactions': set(), 'learning_rate': 0.5}
        self._search_space.update(search_space)
        self._init_config.update(init_config)
        logger.info('search space %s %s %s', self._search_space, self._init_config, self._fixed_hp_config)


def get_y_from_vw_example(vw_example):
    """ get y from a vw_example. this works for regression dataset
    """
    return float(vw_example.split('|')[0])


def get_loss(y_pred, y_true, loss_func='squared'):
    if 'squared' in loss_func:
        loss = mean_squared_error([y_pred], [y_true])
    elif 'absolute' in loss_func:
        loss = mean_absolute_error([y_pred], [y_true])
    else:
        loss = None
        raise NotImplementedError
    return loss


def online_learning_loop(iter_num, vw_examples, vw_alg, loss_func, method_name=''):
    """Implements the online learning loop.
    Args:
        iter_num (int): The total number of iterations
        vw_examples (list): A list of vw examples
        alg (alg instance): An algorithm instance has the following functions:
            - alg.learn(example)
            - alg.predict(example)
        loss_func (str): loss function
    Outputs:
        cumulative_loss_list (list): the list of cumulative loss from each iteration.
            It is returned for the convenience of visualization.
    """
    print('rerunning exp....', len(vw_examples), iter_num)
    loss_list = []
    y_predict_list = []
    for i in range(iter_num):
        vw_x = vw_examples[i]
        y_true = get_y_from_vw_example(vw_x)
        # predict step
        y_pred = vw_alg.predict(vw_x)
        # learn step
        vw_alg.learn(vw_x)
        # calculate one step loss
        loss = get_loss(y_pred, y_true, loss_func)
        loss_list.append(loss)
        y_predict_list.append([y_pred, y_true])

    return loss_list


def get_vw_tuning_problem(tuning_hp='NamesapceInteraction'):
    online_vw_exp_setting = {"max_live_model_num": 5,
                             "fixed_hp_config": {'alg': 'supervised', 'loss_function': 'squared'},
                             "ns_num": 10,
                             "max_iter_num": 10000,
                             }

    # construct openml problem setting based on basic experiment setting
    vw_oml_problem_args = {"max_iter_num": online_vw_exp_setting['max_iter_num'],
                           "dataset_id": '42183',
                           "ns_num": online_vw_exp_setting['ns_num'],
                           "fixed_hp_config": online_vw_exp_setting['fixed_hp_config'],
                           }
    if tuning_hp == 'NamesapceInteraction':
        vw_online_aml_problem = VowpalWabbitNamesspaceTuningProblem(**vw_oml_problem_args)
    elif tuning_hp == 'NamesapceInteraction+LearningRate':
        vw_online_aml_problem = VowpalWabbitNamesspaceLRTuningProblem(**vw_oml_problem_args)
    else:
        NotImplementedError

    return vw_oml_problem_args, vw_online_aml_problem


class TestAutoVW(unittest.TestCase):

    def test_vw_oml_problem_and_vanilla_vw(self):
        vw_oml_problem_args, vw_online_aml_problem = get_vw_tuning_problem()
        vanilla_vw = pyvw.vw(**vw_oml_problem_args["fixed_hp_config"])
        cumulative_loss_list = online_learning_loop(vw_online_aml_problem.max_iter_num,
                                                    vw_online_aml_problem.vw_examples,
                                                    vanilla_vw,
                                                    loss_func=vw_oml_problem_args["fixed_hp_config"].get("loss_function", "squared"),
                                                    )
        print('final average loss:', sum(cumulative_loss_list) / len(cumulative_loss_list))

    def test_supervised_vw_tune_namespace(self):
        # basic experiment setting
        vw_oml_problem_args, vw_online_aml_problem = get_vw_tuning_problem()
        autovw = AutoVW(max_live_model_num=5,
                        search_space=vw_online_aml_problem.search_space,
                        init_config=vw_online_aml_problem.init_config,
                        min_resource_lease='auto',
                        random_seed=2345)

        cumulative_loss_list = online_learning_loop(vw_online_aml_problem.max_iter_num,
                                                    vw_online_aml_problem.vw_examples,
                                                    autovw,
                                                    loss_func=vw_oml_problem_args["fixed_hp_config"].get("loss_function", "squared"),
                                                    )
        print('final average loss:', sum(cumulative_loss_list) / len(cumulative_loss_list))

    def test_supervised_vw_tune_namespace_learningrate(self):
        # basic experiment setting
        vw_oml_problem_args, vw_online_aml_problem = get_vw_tuning_problem(tuning_hp='NamesapceInteraction+LearningRate')
        autovw = AutoVW(max_live_model_num=5,
                        search_space=vw_online_aml_problem.search_space,
                        init_config=vw_online_aml_problem.init_config,
                        min_resource_lease='auto',
                        random_seed=2345)

        cumulative_loss_list = online_learning_loop(vw_online_aml_problem.max_iter_num,
                                                    vw_online_aml_problem.vw_examples,
                                                    autovw,
                                                    loss_func=vw_oml_problem_args["fixed_hp_config"].get("loss_function", "squared"),
                                                    )
        print('final average loss:', sum(cumulative_loss_list) / len(cumulative_loss_list))

    def test_bandit_vw_tune_namespace(self):
        pass

    def test_bandit_vw_tune_namespace_learningrate(self):
        pass


if __name__ == "__main__":
    unittest.main()
