import itertools
from collections import OrderedDict

import ray
from ray.tune.suggest.optuna import OptunaSearch

from flaml import CFO, BlendSearch

SEARCH_ALGO_MAPPING = OrderedDict(
    [
        ("optuna", OptunaSearch),
        ("cfo", CFO),
        ("bs", BlendSearch),
        ("grid", None),
        ("gridbert", None),
        ("rs", None)
    ]
)


class AutoSearchAlgorithm:
    """
    This is a class for getting the search algorithm based on the search algorithm name
    (a string variable) instantiated as one of the algorithms of the library when
    created with the `~flaml.nlp.hpo.AutoSearchAlgorithm.from_method_name` method.

    This class cannot be instantiated directly using ``__init__()`` (throws an error).
    """

    def __init__(self):
        raise EnvironmentError(
            "AutoSearchAlgorithm is designed to be instantiated "
            "using the `AutoSearchAlgorithm.from_method_name(cls, search_algo_name, search_algo_args_mode,"
            " hpo_search_space, **custom_hpo_args)` methods."
        )

    @classmethod
    def from_method_name(cls, search_algo_name, search_algo_args_mode, hpo_search_space, **custom_hpo_args):
        """
        Instantiating one of the search algorithm classes based on the search algorithm name, search algorithm
        argument mode, hpo search space and other keyword args

        Args:
            search_algo_name:
                A string variable that specifies the search algorithm name, e.g., "bs"

            search_algo_args_mode:
                A string variable that specifies the mode for the search algorithm args, e.g., "dft" means
                initializing using the default mode

            hpo_search_space:
                The hpo search space

            custom_hpo_args:
                The customized arguments for the search algorithm (specified by user)

        Example:
        >>> from flaml.nlp.hpo.hpo_searchspace import AutoHPOSearchSpace
        >>> search_space_hpo=AutoHPOSearchSpace.from_model_and_dataset_name("uni", "electra", "small", ["glue"], "rte")
        >>> search_algo = AutoSearchAlgorithm.from_method_name("bs", "cus", search_space_hpo,
                         {"points_to_evaluate": [{"learning_rate": 1e-5, "num_train_epochs": 10}])
        """

        assert hpo_search_space, "hpo_search_space needs to be specified for calling AutoSearchAlgorithm.from_method_name"
        if not search_algo_name:
            search_algo_name = "grid"
        if search_algo_name in SEARCH_ALGO_MAPPING.keys():
            if SEARCH_ALGO_MAPPING[search_algo_name] is None:
                return None
            """
            filtering the customized args for hpo from custom_hpo_args, keep those
            which are in the input variable name list of the constructor of
            the algorithm, remove those which does not appear in the input variables
            of the constructor function
            """
            this_search_algo_kwargs = None
            allowed_arguments = SEARCH_ALGO_MAPPING[search_algo_name].__init__.__code__.co_varnames
            allowed_custom_args = {key: custom_hpo_args[key] for key in custom_hpo_args.keys() if
                                   key in allowed_arguments}

            """
             If the search_algo_args_mode is "dft", set the args to the default args, e.g.,the default args for
             BlendSearch is "low_cost_partial_config": {"num_train_epochs": min_epoch,"per_device_train_batch_size"
             : max(hpo_search_space["per_device_train_batch_size"].categories)},
            """
            if search_algo_args_mode == "dft":
                this_search_algo_kwargs = DEFAULT_SEARCH_ALGO_ARGS_MAPPING[search_algo_name](
                    "dft", hpo_search_space=hpo_search_space, **allowed_custom_args)
            elif search_algo_args_mode == "cus":
                this_search_algo_kwargs = DEFAULT_SEARCH_ALGO_ARGS_MAPPING[search_algo_name](
                    "cus", hpo_search_space=hpo_search_space, **allowed_custom_args)

            """
            returning the hpo algorithm with the arguments
            """
            return SEARCH_ALGO_MAPPING[search_algo_name](**this_search_algo_kwargs)
        raise ValueError(
            "Unrecognized method {} for this kind of AutoSearchAlgorithm: {}.\n"
            "Method name should be one of {}.".format(
                search_algo_name, cls.__name__, ", ".join(SEARCH_ALGO_MAPPING.keys())
            )
        )

    @staticmethod
    def grid2list(grid_config):
        key_val_list = [[(key, each_val) for each_val in val_list['grid_search']]
                        for (key, val_list) in grid_config.items()]
        config_list = [dict(x) for x in itertools.product(*key_val_list)]
        return config_list


def get_search_algo_args_optuna(search_args_mode, hpo_search_space=None, **custom_hpo_args):
    return {}


def default_search_algo_args_bs(search_args_mode, hpo_search_space=None, **custom_hpo_args):
    assert hpo_search_space, "hpo_search_space needs to be specified for calling AutoSearchAlgorithm.from_method_name"
    if "num_train_epochs" in hpo_search_space and \
            isinstance(hpo_search_space["num_train_epochs"], ray.tune.sample.Categorical):
        min_epoch = min(hpo_search_space["num_train_epochs"].categories)
    else:
        assert isinstance(hpo_search_space["num_train_epochs"], ray.tune.sample.Float)
        min_epoch = hpo_search_space["num_train_epochs"].lower
    default_search_algo_args = {
        "low_cost_partial_config": {
            "num_train_epochs": min_epoch,
            "per_device_train_batch_size": max(hpo_search_space["per_device_train_batch_size"].categories),
        },
    }
    if search_args_mode == "cus":
        default_search_algo_args.update(custom_hpo_args)
    return default_search_algo_args


def experiment_search_algo_args_bs(hpo_search_space=None):
    if "num_train_epochs" in hpo_search_space and \
            isinstance(hpo_search_space["num_train_epochs"], ray.tune.sample.Categorical):
        min_epoch = min(hpo_search_space["num_train_epochs"].categories)
    else:
        assert isinstance(hpo_search_space["num_train_epochs"], ray.tune.sample.Float)
        min_epoch = hpo_search_space["num_train_epochs"].lower
    default_search_algo_args = {
        "low_cost_partial_config": {
            "num_train_epochs": min_epoch,
        },
    }
    return default_search_algo_args


def default_search_algo_args_skopt(hpo_search_space=None):
    return {}


def default_search_algo_args_dragonfly(hpo_search_space=None):
    return {}


def default_search_algo_args_nevergrad(hpo_search_space=None):
    return {}


def default_search_algo_args_hyperopt(hpo_search_space=None):
    return {}


def default_search_algo_args_grid_search(search_args_mode, hpo_search_space=None, **custom_hpo_args):
    return {}


def default_search_algo_args_random_search(search_args_mode, hpo_search_space=None, **custom_hpo_args):
    return {}


DEFAULT_SEARCH_ALGO_ARGS_MAPPING = OrderedDict(
    [
        ("optuna", get_search_algo_args_optuna),
        ("cfo", default_search_algo_args_bs),
        ("bs", default_search_algo_args_bs),
        ("grid", default_search_algo_args_grid_search),
        ("gridbert", default_search_algo_args_random_search)
    ]
)
