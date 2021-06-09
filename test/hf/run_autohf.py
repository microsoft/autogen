'''Require: pip install torch transformers datasets wandb flaml[blendsearch,ray]
'''
# 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
import os
import shutil

from flaml.nlp import AutoTransformers
from flaml.nlp import AzureUtils, JobID
from flaml.nlp.utils import load_console_args

global azure_log_path
global azure_key


def get_resplit_portion(jobid_config):
    if jobid_config.dat == ["glue"] and jobid_config.subdat in {"mnli"}:
        return {"source": ["train", "validation_matched"], "train": [0, 0.8], "validation": [0.8, 0.9],
                "test": [0.9, 1.0]}
    else:
        return {"source": ["train", "validation"], "train": [0, 0.8], "validation": [0.8, 0.9], "test": [0.9, 1.0]}


def get_preparedata_setting(args, jobid_config):
    preparedata_setting = {
        "server_name": args.server_name,
        "data_root_path": args.data_root_dir,
        "max_seq_length": 128,
        "jobid_config": jobid_config,
        "is_wandb_on": True
    }
    if jobid_config.spt == 'rspt':
        preparedata_setting["resplit_portion"] = get_resplit_portion(jobid_config)
    if ("albert" == jobid_config.pre and jobid_config.dat == ["squad"]) or \
            ("funnel" in jobid_config.pre and jobid_config.dat[0] in {"imdb", "yelp_review_full", "yelp_polarity",
                                                                      "amazon_polarity", "amazon_review_multi"}):
        preparedata_setting["max_seq_length"] = 512
    if jobid_config.dat[0] == "glue" and jobid_config.subdat == "mnli":
        preparedata_setting["fold_name"] = ['train', 'validation_matched', 'test_matched']
    return preparedata_setting


def get_autohf_settings(args, **custom_args):
    autohf_settings = {"resources_per_trial": {"gpu": 1, "cpu": 1},
                       "num_samples": args.sample_num,
                       "time_budget": args.time_budget,
                       "ckpt_per_epoch": 1,
                       }
    for other_attr in ["ds_config", "rep_id"]:
        if hasattr(args, other_attr):
            autohf_settings[other_attr] = getattr(args, other_attr)
        else:
            autohf_settings[other_attr] = None
    if len(custom_args) > 0:
        autohf_settings.update(custom_args)
    return autohf_settings


def rm_home_result():
    from os.path import expanduser
    home = expanduser("~")
    if os.path.exists(home + "/ray_results/"):
        shutil.rmtree(home + "/ray_results/")


def get_best_base_config(args, jobid_config, autohf):
    import copy
    import re
    args_small = copy.deepcopy(args)
    args_small.algo_name = "optuna"
    args_small.search_alg_args_mode = "dft"
    args_small.algo_mode = "hpo"
    args_small.space_mode = "uni"
    args_small.pruner = "None"

    if "funnel" not in args_small.pretrained_model_size:
        args_small.algo_mode = "hpo"
    else:
        args_small.algo_mode = "list"
    args_small.sample_num = 10000
    args_small.time_budget = 3600
    args_small.rep_id = 0
    jobid_config_small = JobID(args_small)
    if jobid_config_small.pre == "deberta":
        jobid_config_small.presz = "base"
    else:
        jobid_config_small.presz = "small"
    jobid_config_small.pre_full = re.sub("(xlarge|large|intermediate)", jobid_config_small.presz,
                                         jobid_config_small.pre_full)
    azure_utils_small = AzureUtils(
        console_args=args_small,
        jobid=jobid_config_small,
        autohf=autohf)
    preparedata_setting = get_preparedata_setting(args, jobid_config)
    autohf.prepare_data(**preparedata_setting)
    autohf.set_metric()

    best_config = azure_utils_small.get_ranked_configs(autohf.metric_mode_name)[0]
    return best_config


def search_base_and_search_lower_lr(args, jobid_config, autohf):
    best_config = get_best_base_config(args, jobid_config, autohf)

    import copy
    args_large = copy.deepcopy(args)
    args_large.time_budget = args.time_budget - 3600
    args_large.sample_num = 100000
    args_large.algo_name = args.algo_name
    args_large.search_alg_args_mode = "cus"
    args_large.space_mode = "buni"
    args_large.pruner = "None"
    jobid_config_large = JobID(args_large)
    jobid_config_large.presz = jobid_config.presz
    jobid_config_large.pre_full = jobid_config.pre_full
    azure_utils_large = AzureUtils(console_args=args_large, jobid=jobid_config_large, autohf=autohf)

    _test_hpo(args_large,
              jobid_config_large,
              autohf,
              azure_utils_large,
              autohf_settings=get_autohf_settings(args_large, **{"points_to_evaluate": [best_config],
                                                                 "bound": {"learning_rate": {
                                                                     "u": best_config["learning_rate"]}}}))


def search_base_and_search_around_best(args, jobid_config, autohf):
    args.algo_name = "bs"
    args.search_alg_args_mode = "dft"
    args.spa = "uni"
    args.pru = "None"
    best_config = get_best_base_config(args, jobid_config, autohf)

    import copy
    args_large = copy.deepcopy(args)
    args_large.time_budget = args.time_budget - 3600
    args_large.sample_num = 100000
    args_large.algo_name = "cfo"
    args_large.search_alg_args_mode = "cus"
    args_large.space_mode = "uni"
    jobid_config_large = JobID(args_large)
    jobid_config_large.presz = jobid_config.presz
    jobid_config_large.pre_full = jobid_config.pre_full
    azure_utils_large = AzureUtils(console_args=args_large, jobid=jobid_config_large, autohf=autohf)

    _test_hpo(args_large,
              jobid_config_large,
              autohf,
              azure_utils_large,
              autohf_settings=get_autohf_settings(args_large, **{"points_to_evaluate": [best_config]}))


def evaluate_configs(autohf, args, ranked_all_configs):
    import copy
    this_args = copy.deepcopy(args)
    this_args.time_budget = 100000
    this_args.sample_num = int(len(ranked_all_configs))
    this_args.search_alg_args_mode = "cus"
    jobid_config = JobID(this_args)
    azure_utils_large = AzureUtils(console_args=this_args, jobid=jobid_config, autohf=autohf)
    _test_hpo(this_args,
              jobid_config,
              autohf,
              azure_utils_large,
              autohf_settings=get_autohf_settings(this_args, **{"points_to_evaluate": ranked_all_configs}))


def convert_config_to_different_size(origin_config, mode):
    import re
    import copy
    if mode == "small":
        new_config = copy.deepcopy(origin_config)
        if new_config.pre == "funnel":
            new_config.mod = "list"
        else:
            new_config.mod = "hpo"
        if new_config.pre == "funnel":
            new_config.presz = "small"
        else:
            new_config.presz = "base"
        new_config.pre_full = re.sub("(xlarge|large|intermediate)", new_config.presz, origin_config.pre_full)
    elif mode == "large":
        new_config = copy.deepcopy(origin_config)
        new_config.mod = "hpo"
        if new_config.pre == "funnel":
            new_config.presz = "xlarge"
            new_config.pre_full = re.sub("(small)", "xlarge", origin_config.pre_full)
        else:
            new_config.presz = "large"
            new_config.pre_full = re.sub("(small)", "large", origin_config.pre_full)

    return new_config


def evaluate_small_best_configs_on_large(large_args, autohf):
    jobid_config_small = convert_config_to_different_size(JobID(large_args), mode="small")
    jobid_config_small.rep = 0
    azure_utils_small = AzureUtils(console_args=None, jobid=jobid_config_small, autohf=autohf)
    ranked_all_small_configs = azure_utils_small.get_ranked_configs(autohf.metric_mode_name)
    evaluate_configs(large_args, ranked_all_small_configs[:int(len(ranked_all_small_configs) / 2)])


def add_dict_item_to_list(this_list, this_dict):
    is_exist = len([x for x in this_list if x == this_dict]) > 0
    if not is_exist:
        this_list.append(this_dict)
    return this_list


def evaluate_large_best_configs_on_small(small_args, autohf):
    jobid_config_large = convert_config_to_different_size(JobID(small_args), mode="large")
    autohf.jobid_config = jobid_config_large
    autohf.set_metric()
    all_configs_from_large = []
    for rep_id in range(3):
        jobid_config_large.rep = rep_id
        azure_utils_large = AzureUtils(console_args=small_args, jobid=jobid_config_large, autohf=autohf)
        ranked_all_large_configs = azure_utils_large.get_ranked_configs(autohf.metric_mode_name)
        for each_config in ranked_all_large_configs:
            all_configs_from_large = add_dict_item_to_list(all_configs_from_large, each_config)
    jobid_config_small = convert_config_to_different_size(JobID(small_args), mode="small")
    jobid_config_small.rep = 0
    azure_utils_small = AzureUtils(console_args=small_args, jobid=jobid_config_small, autohf=autohf)
    ranked_all_small_configs = azure_utils_small.get_ranked_configs(autohf.metric_mode_name)
    for each_config in ranked_all_small_configs:
        all_configs_from_large = add_dict_item_to_list(all_configs_from_large, each_config)

    evaluate_configs(autohf, small_args, list(all_configs_from_large))


def _test_hpo(args,
              jobid_config,
              autohf,
              azure_utils=None,
              autohf_settings=None,
              ):
    try:
        if not azure_utils:
            azure_utils = AzureUtils(console_args=args, jobid=jobid_config, autohf=autohf)
        preparedata_setting = get_preparedata_setting(args, jobid_config)
        autohf.prepare_data(**preparedata_setting)

        analysis = validation_metric = test_metric = None
        if not autohf_settings:
            autohf_settings = get_autohf_settings(args)
        if args.algo_mode != "hfhpo":
            validation_metric, analysis = autohf.fit(**autohf_settings, )
        else:
            autohf.fit_hf(**autohf_settings)

        if jobid_config.spt == "ori":
            predictions, test_metric = autohf.predict()
            if validation_metric:
                test_metric.update({"validation": validation_metric})
        else:
            predictions = None
            if test_metric:
                validation_metric.update({"test": test_metric})

        if analysis is not None:
            json_log = azure_utils.extract_log_from_analysis(analysis)
        else:
            json_log = None
        azure_utils.write_autohf_output(json_log=json_log,
                                        valid_metric=validation_metric,
                                        predictions=predictions,
                                        duration=autohf.last_run_duration)

    except AssertionError:
        azure_utils.write_exception()
    rm_home_result()


if __name__ == "__main__":
    autohf = AutoTransformers()
    args = load_console_args()
    jobid_config = JobID(args)

    if args.algo_mode in ("hpo", "hfhpo", "grid", "gridbert"):
        _test_hpo(args, jobid_config, autohf)
    elif args.algo_mode == "bestnn":
        search_base_and_search_lower_lr(args, jobid_config, autohf)
    elif args.algo_mode == "list":
        evaluate_small_best_configs_on_large(args, autohf)
    elif args.algo_mode == "list_s":
        evaluate_large_best_configs_on_small(args, autohf)
