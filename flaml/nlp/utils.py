import argparse
import json
import os
import pathlib
import re
from dataclasses import dataclass, field


def dataset_subdataset_name_format_check(val_str):
    regex = re.compile(r"^[^:]*:[^:]*$")
    if (val_str is not None) and (not regex.search(val_str)):
        raise argparse.ArgumentTypeError("dataset_subdataset_name must be in the format {data_name}:{subdata_name}")
    return val_str


def pretrained_model_size_format_check(val_str):
    regex = re.compile(r"^[^:]*:(small|base|large|xlarge)")
    if (val_str is not None) and (not regex.search(val_str)):
        raise argparse.ArgumentTypeError("pretrained_model_size must be in the format {model_name}:{model_size},"
                                         "where {model_name} is the name from huggingface.co/models, {model_size}"
                                         "is chosen from small, base, large, xlarge")
    return val_str


def load_dft_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--server_name', type=str, help='server name', required=False,
                            choices=["tmdev", "dgx", "azureml"], default="tmdev")
    arg_parser.add_argument('--algo_mode', type=str, help='hpo or grid search', required=False,
                            choices=["grid", "hpo", "hfhpo"], default="hpo")
    arg_parser.add_argument('--data_root_dir', type=str, help='data dir', required=False, default="data/")
    arg_parser.add_argument('--dataset_subdataset_name', type=dataset_subdataset_name_format_check,
                            help='dataset and subdataset name', required=False, default=None)
    arg_parser.add_argument('--space_mode', type=str, help='space mode', required=False,
                            choices=["grid", "gnr", "uni", "uni_test", "cus", "buni"], default="uni")
    arg_parser.add_argument('--search_alg_args_mode', type=str, help='search algorithm args mode', required=False,
                            choices=["dft", "exp", "cus"], default="dft")
    arg_parser.add_argument('--algo_name', type=str, help='algorithm', required=False,
                            choices=["bs", "optuna", "cfo", "rs"], default="bs")
    arg_parser.add_argument('--pruner', type=str, help='pruner', required=False,
                            choices=["asha", "None"], default="None")
    arg_parser.add_argument('--pretrained_model_size', type=pretrained_model_size_format_check,
                            help='pretrained model', required=False, default=None)
    arg_parser.add_argument('--sample_num', type=int, help='sample num', required=False, default=None)
    arg_parser.add_argument('--time_budget', type=int, help='time budget', required=False, default=None)
    arg_parser.add_argument('--time_as_grid', type=int, help='time as grid search', required=False, default=None)
    arg_parser.add_argument('--rep_id', type=int, help='rep id', required=False, default=0)
    arg_parser.add_argument('--azure_key', type=str, help='azure key', required=False, default=None)
    arg_parser.add_argument('--resplit_mode', type=str, help='resplit mode', required=False,
                            choices=["rspt", "ori"], default="ori")
    arg_parser.add_argument('--ds_config', type=str, help='deep speed config file path',
                            required=False, default=None)
    arg_parser.add_argument('--yml_file', type=str, help='yml file path', required=False, default="test.yml")
    arg_parser.add_argument('--key_path', type=str, help='path for key.json', required=False, default=None)
    arg_parser.add_argument('--root_log_path', type=str, help='root path for log', required=False, default="logs_azure")
    arg_parser.add_argument('--round_idx', type=int, help='round idx for acl experiments', required=False, default=0)
    arg_parser.add_argument('--seed_data', type=int, help='seed of data shuffling', required=False, default=43)
    arg_parser.add_argument('--seed_transformers', type=int, help='seed of transformers', required=False, default=42)
    console_args, unknown = arg_parser.parse_known_args()
    return console_args


def merge_dicts(dict1, dict2):
    for key2 in dict2.keys():
        if key2 in dict1:
            dict1_vals = set(dict1[key2])
            dict2_vals = set(dict2[key2])
            dict1[key2] = list(dict1_vals.union(dict2_vals))
        else:
            dict1[key2] = dict2[key2]
    return dict1


def _check_dict_keys_overlaps(dict1: dict, dict2: dict):
    dict1_keys = set(dict1.keys())
    dict2_keys = set(dict2.keys())
    return len(dict1_keys.intersection(dict2_keys)) > 0


def _variable_override_default_alternative(obj_ref, var_name, default_value, all_values, overriding_value=None):
    """
        Setting the value of var. If overriding_value is specified, var is set to overriding_value;
        If overriding_value is not specified, var is set to default_value meanwhile showing all_values
    """
    assert isinstance(all_values, list)
    if overriding_value:
        setattr(obj_ref, var_name, overriding_value)
        print("The value for {} is specified as {}".format(var_name, overriding_value))
    else:
        setattr(obj_ref, var_name, default_value)
        print("The value for {} is not specified, setting it to the default value {}. "
              "Alternatively, you can set it to {}".format(var_name, default_value, ",".join(all_values)))


@dataclass
class PathUtils:
    hpo_ckpt_path: str = field(metadata={"help": "the directory for hpo output"})
    hpo_result_path: str = field(metadata={"help": "the directory for hpo result"})
    hpo_log_path: str = field(metadata={"help": "the directory for log"})
    hpo_config_path: str = field(metadata={"help": "the directory for log"})

    log_dir_per_run: str = field(metadata={"help": "log directory for each run."})
    result_dir_per_run: str = field(metadata={"help": "result directory for each run."})
    ckpt_dir_per_run: str = field(metadata={"help": "checkpoint directory for each run."})
    ckpt_dir_per_trial: str = field(metadata={"help": "checkpoint directory for each trial."})

    def __init__(self,
                 jobid_config,
                 hpo_data_root_path,
                 ):
        self.jobid_config = jobid_config
        self.hpo_data_root_path = hpo_data_root_path
        self.hpo_ckpt_path = os.path.join(hpo_data_root_path, "checkpoint")
        self.hpo_result_path = os.path.join(hpo_data_root_path, "result")
        self.hpo_log_path = self.hpo_result_path

    @staticmethod
    def init_and_make_one_dir(dir_path):
        assert dir_path
        if not os.path.exists(dir_path):
            pathlib.Path(dir_path).mkdir(parents=True, exist_ok=True)

    def make_dir_per_run(self):
        jobid_str = self.jobid_config.to_jobid_string()
        self.ckpt_dir_per_run = os.path.join(self.hpo_ckpt_path, jobid_str)
        PathUtils.init_and_make_one_dir(self.ckpt_dir_per_run)

        self.result_dir_per_run = os.path.join(self.hpo_result_path, jobid_str)
        PathUtils.init_and_make_one_dir(self.result_dir_per_run)

        self.log_dir_per_run = os.path.join(self.hpo_log_path, jobid_str)
        PathUtils.init_and_make_one_dir(self.log_dir_per_run)

    def make_dir_per_trial(self, trial_id):
        jobid_str = self.jobid_config.to_jobid_string()
        ckpt_dir_per_run = os.path.join(self.hpo_ckpt_path, jobid_str)
        self.ckpt_dir_per_trial = os.path.join(ckpt_dir_per_run, jobid_str, trial_id)
        PathUtils.init_and_make_one_dir(self.ckpt_dir_per_trial)
