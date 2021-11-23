import os
import pytest


@pytest.mark.skipif(os.name == "posix", reason="do not run on mac os")
def test_max_iter_1():
    from flaml import AutoML

    from datasets import load_dataset

    train_dataset = load_dataset("glue", "mrpc", split="train").to_pandas().iloc[0:4]
    dev_dataset = load_dataset("glue", "mrpc", split="train").to_pandas().iloc[0:4]

    custom_sent_keys = ["sentence1", "sentence2"]
    label_key = "label"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    automl = AutoML()

    def toy_metric(
        X_test,
        y_test,
        estimator,
        labels,
        X_train,
        y_train,
        weight_test=None,
        weight_train=None,
        config=None,
        groups_test=None,
        groups_train=None,
    ):
        return 0, {
            "test_loss": 0,
            "train_loss": 0,
            "pred_time": 0,
        }

    automl_settings = {
        "gpu_per_trial": 0,
        "max_iter": 1,
        "time_budget": 5,
        "task": "seq-classification",
        "metric": toy_metric,
        "log_file_name": "seqclass.log",
    }

    automl_settings["custom_hpo_args"] = {
        "model_path": "google/electra-small-discriminator",
        "output_dir": "data/output/",
        "ckpt_per_epoch": 5,
        "fp16": False,
    }

    automl.fit(
        X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings
    )
    del automl
