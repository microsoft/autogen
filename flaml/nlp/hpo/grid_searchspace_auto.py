from collections import OrderedDict

from .get_grid_search_space import \
    (get_electra_space,
     get_bert_space,
     get_roberta_space,
     get_funnel_space,
     get_deberta_space,
     get_albert_space,
     get_longformer_space,
     get_mobilebert_space
     )

GRID_SEARCH_SPACE_MAPPING = OrderedDict(
    [
        ("electra", get_electra_space),
        ("bert", get_bert_space),
        ("roberta", get_roberta_space),
        ("funnel", get_funnel_space),
        ("deberta", get_deberta_space),
        ("albert", get_albert_space),
        ("mobilebert", get_mobilebert_space),
        ("longformer", get_longformer_space)
    ]
)

HF_MODEL_LIST = [
    "bert",
    "roberta",
    "electra",
    "xlnet",
    "albert",
    "distilbert",
    "deberta",
    "mobilebert",
    "funnel"
]


class AutoGridSearchSpace:
    """
    This is a class for getting the recommended grid search space of a pre-trained LM that will be
    instantiated as one of the search spaces of the library when created with the
    `~flaml.nlp.hpo.AutoGridSearchSpace.from_model_and_dataset_name` method.

    This class cannot be instantiated directly using ``__init__()`` (throws an error).
    """

    def __init__(self):
        raise EnvironmentError(
            "AutoGridSearchSpace is designed to be instantiated "
            "using the `AutoGridSearchSpace.from_config_and_method_name(cls, model_type, model_size_type,"
            "dataset_name,subdataset_name = None,algo_mode = None)` methods."
        )

    @classmethod
    def from_model_and_dataset_name(cls,
                                    model_type,
                                    model_size_type,
                                    dataset_name_list: list = None,
                                    subdataset_name=None,
                                    algo_mode=None):
        """
        Instantiate one of the classes for getting the recommended grid search space of a pre-trained LM from
        the model type, model size type, dataset name, sub dataset name and algorithm mode

        Args:
            model_type:
                A string variable which is the model type, e.g. "electra"

            model_size_type:
                A string variable which is the size of the model, e.g., "small"

            dataset_name_list:
                A string variable which is the dataset name, e.g., "glue"

            subdataset_name:
                A string variable which is the sub dataset name,e.g., "rte"

            algo_mode:
                A string variable which is the algorithm mode for grid search, e.g., "gridbert"

        Example:
            >>> AutoGridSearchSpace.from_model_and_dataset_name("electra", "small", ["glue"], "rte", "grid")

        """

        if model_type in GRID_SEARCH_SPACE_MAPPING.keys():
            this_model_recommended_space = GRID_SEARCH_SPACE_MAPPING[model_type](
                model_size_type, dataset_name_list, subdataset_name, algo_mode)
            return this_model_recommended_space
        raise ValueError(
            "Unrecognized method {},{} for this kind of AutoGridSearchSpace: {}.\n"
            "Method name should be one of {}.".format(
                model_type, dataset_name_list, cls.__name__, ", ".join(GRID_SEARCH_SPACE_MAPPING.keys())
            )
        )
