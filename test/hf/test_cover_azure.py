"""
    test suites for covering azure_utils.py
"""


def get_preparedata_setting(jobid_config):
    preparedata_setting = {
        "server_name": "tmdev",
        "data_root_path": "data/",
        "max_seq_length": 128,
        "jobid_config": jobid_config,
        "resplit_portion": {"source": ["train", "validation"],
                            "train": [0, 0.8],
                            "validation": [0.8, 0.9],
                            "test": [0.9, 1.0]}
    }
    return preparedata_setting


def get_console_args():
    from flaml.nlp.utils import load_dft_args
    args = load_dft_args()
    args.dataset_subdataset_name = "glue:mrpc"
    args.algo_mode = "hpo"
    args.space_mode = "uni"
    args.search_alg_args_mode = "dft"
    args.algo_name = "bs"
    args.pruner = "None"
    args.pretrained_model_size = "google/electra-base-discriminator:base"
    args.resplit_mode = "rspt"
    args.rep_id = 0
    args.seed_data = 43
    args.seed_transformers = 42
    return args


def test_get_configblob_from_partial_jobid():
    try:
        import ray
    except ImportError:
        return

    from flaml.nlp.result_analysis.azure_utils import JobID
    each_blob_name = "dat=glue_subdat=cola_mod=grid_spa=cus_arg=dft_alg=grid" \
                     "_pru=None_pre=deberta_presz=large_spt=rspt_rep=0_sddt=43" \
                     "_sdhf=42_var1=1e-05_var2=0.0.json"
    partial_jobid = JobID()
    partial_jobid.pre = "deberta"
    partial_jobid.mod = "grid"
    partial_jobid.spa = "cus"
    partial_jobid.presz = "large"

    each_jobconfig = JobID.convert_blobname_to_jobid(each_blob_name)
    each_jobconfig.is_match(partial_jobid)

    partial_jobid = JobID()
    partial_jobid.pre = "deberta"
    partial_jobid.mod = "hpo"
    partial_jobid.spa = "cus"
    partial_jobid.presz = "large"
    partial_jobid.sddt = None

    each_jobconfig = JobID.convert_blobname_to_jobid(each_blob_name)
    each_jobconfig.is_match(partial_jobid)


def test_jobid():
    try:
        import ray
    except ImportError:
        return

    from flaml.nlp.result_analysis.azure_utils import JobID
    args = get_console_args()

    jobid_config = JobID(args)
    jobid_config.to_partial_jobid_string()
    JobID.convert_blobname_to_jobid("test")
    JobID.dataset_list_to_str("glue")
    JobID.get_full_data_name(["glue"], "mrpc")
    JobID._extract_model_type_with_keywords_match("google/electra-base-discriminator:base")

    jobid_config.to_wandb_string()


def test_azureutils():
    try:
        import ray
    except ImportError:
        return

    from flaml.nlp.result_analysis.azure_utils import AzureUtils, ConfigScore, JobID, ConfigScoreList
    from flaml.nlp import AutoTransformers

    args = get_console_args()
    args.key_path = "."
    jobid_config = JobID(args)
    autohf = AutoTransformers()
    autohf.jobid_config = jobid_config

    preparedata_setting = get_preparedata_setting(jobid_config)
    autohf.prepare_data(**preparedata_setting)

    each_configscore = ConfigScore(trial_id="test", start_time=0.0, last_update_time=0.0,
                                   config={}, metric_score={"max": 0.0}, time_stamp=0.0)
    configscore_list = ConfigScoreList([each_configscore])
    for each_method in ["unsorted", "sort_time", "sort_accuracy"]:
        configscore_list.sorted(each_method)
    configscore_list.get_best_config()

    azureutils = AzureUtils(console_args=args, autohf=autohf)
    azureutils.autohf = autohf
    azureutils.root_log_path = "logs_azure/"

    azureutils.write_autohf_output(configscore_list=[each_configscore],
                                   valid_metric={},
                                   predictions=[],
                                   duration=0)

    azureutils.get_config_and_score_from_partial_jobid(root_log_path="data/", partial_jobid=jobid_config)


if __name__ == "__main__":
    test_get_configblob_from_partial_jobid()
    test_jobid()
    test_azureutils()
