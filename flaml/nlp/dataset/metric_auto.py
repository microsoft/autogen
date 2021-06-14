# https://github.com/huggingface/datasets/blob/master/metrics/glue/glue.py
from collections import OrderedDict
import typing

metric_mode_mapping_glue = {
    "cola": [("matthews_correlation", "max")],
    "mnli": [("accuracy", "max")],
    "mrpc": [("accuracy", "max"), ("f1", "max")],
    "qnli": [("accuracy", "max")],
    "qqp": [("accuracy", "max"), ("f1", "max")],
    "rte": [("accuracy", "max")],
    "sst2": [("accuracy", "max")],
    "stsb": [("pearson", "max"), ("spearmanr", "max")],
    "wnli": [("accuracy", "max")]
}

metric_mode_mapping_squad = [("exact_match", "max"), ("f1", "max")]

metric_mode_mapping_super_glue = {
    "axb": [("matthews_correlation", "max")],
    "cb": [("accuracy", "max"), ("f1", "max")],
    "copa": [("accuracy", "max")],
    "rte": [("accuracy", "max")],
    "wic": [("accuracy", "max")],
    "wsc": [("accuracy", "max")],
    "wsc.fixed": [("accuracy", "max")],
    "boolq": [("accuracy", "max")],
    "axg": [("accuracy", "max")]
}

metric_mode_mapping_imdb = [("accuracy", "max")]

metric_mode_mapping_yelp = [("accuracy", "max")]

METRIC_MAPPING = OrderedDict(
    [
        ("squad", metric_mode_mapping_squad),
        ("glue", metric_mode_mapping_glue),
        ("super_glue", metric_mode_mapping_super_glue),
        ("imdb", metric_mode_mapping_imdb),
        ("yelp_review_full", metric_mode_mapping_yelp)
    ]
)


def get_default_and_alternative_metric(dataset_name_list: typing.List,
                                       subdataset_name=None,
                                       custom_metric_name=None,
                                       custom_metric_mode_name=None):
    from ..result_analysis.azure_utils import JobID
    dataset_name = JobID.dataset_list_to_str(dataset_name_list)
    if dataset_name not in METRIC_MAPPING.keys():
        assert custom_metric_name and custom_metric_mode_name, \
            "The dataset is not in {}, you must explicitly specify " \
            "the custom_metric_name and custom_metric_mode_name".format(",".join(METRIC_MAPPING.keys()))
    eval_name_mapping = METRIC_MAPPING[dataset_name]
    if isinstance(eval_name_mapping, dict):
        assert subdataset_name and subdataset_name in eval_name_mapping, \
            "dataset_name and subdataset_name not correctly specified"
        default_metric, default_mode = eval_name_mapping[subdataset_name][0]
        all_metrics, all_mode \
            = [x[0] for x in eval_name_mapping[subdataset_name]] \
            + ["loss"], [x[1] for x in eval_name_mapping[subdataset_name]] + ["min"]

        return default_metric, default_mode, all_metrics, all_mode
    else:
        assert isinstance(eval_name_mapping, list), "dataset_name and subdataset_name not correctly specified"

        default_metric, default_mode = eval_name_mapping[0]
        all_metrics, all_mode = [x[0] for x in eval_name_mapping] + ["loss"], \
                                [x[1] for x in eval_name_mapping] + ["min"]

        return default_metric, default_mode, all_metrics, all_mode
