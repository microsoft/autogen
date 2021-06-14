'''Require: pip install torch transformers datasets wandb flaml[blendsearch,ray]
'''
global azure_log_path
global azure_key


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


def get_autohf_settings():
    autohf_settings = {"resources_per_trial": {"cpu": 1},
                       "num_samples": 1,
                       "time_budget": 100000,
                       "ckpt_per_epoch": 1,
                       "fp16": False,
                       "ray_local_mode": True
                       }
    return autohf_settings


def test_hpo():
    try:
        import ray
    except ImportError:
        return

    from flaml.nlp import AutoTransformers
    from flaml.nlp import JobID
    from flaml.nlp import AzureUtils

    jobid_config = JobID()
    jobid_config.set_unittest_config()
    autohf = AutoTransformers()

    preparedata_setting = get_preparedata_setting(jobid_config)
    autohf.prepare_data(**preparedata_setting)

    autohf_settings = get_autohf_settings()
    autohf_settings["points_to_evaluate"] = [{"learning_rate": 2e-5}]
    validation_metric, analysis = autohf.fit(**autohf_settings)

    predictions, test_metric = autohf.predict()
    if test_metric:
        validation_metric.update({"test": test_metric})

    azure_utils = AzureUtils(root_log_path="logs_test/", autohf=autohf)
    azure_utils._azure_key = "test"
    azure_utils._container_name = "test"

    configscore_list = azure_utils.extract_configscore_list_from_analysis(analysis)
    azure_utils.write_autohf_output(configscore_list=configscore_list,
                                    valid_metric=validation_metric,
                                    predictions=predictions,
                                    duration=autohf.last_run_duration)

    jobid_config.mod = "grid"
    autohf = AutoTransformers()

    preparedata_setting = get_preparedata_setting(jobid_config)
    autohf.prepare_data(**preparedata_setting)


if __name__ == "__main__":
    test_hpo()
