import sys
import pytest
import requests


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_summarization():
    from flaml import AutoML
    from pandas import DataFrame

    train_dataset = DataFrame(
        [
            ("The cat is alive", "The cat is dead"),
            ("The cat is alive", "The cat is dead"),
            ("The cat is alive", "The cat is dead"),
            ("The cat is alive", "The cat is dead"),
        ]
    )
    dev_dataset = DataFrame(
        [
            ("The old woman is beautiful", "The old woman is ugly"),
            ("The old woman is beautiful", "The old woman is ugly"),
            ("The old woman is beautiful", "The old woman is ugly"),
            ("The old woman is beautiful", "The old woman is ugly"),
        ]
    )
    test_dataset = DataFrame(
        [
            ("The purse is cheap", "The purse is expensive"),
            ("The purse is cheap", "The purse is expensive"),
            ("The purse is cheap", "The purse is expensive"),
            ("The purse is cheap", "The purse is expensive"),
        ]
    )

    for each_dataset in [train_dataset, dev_dataset, test_dataset]:
        each_dataset.columns = ["document", "summary"]

    custom_sent_keys = ["document"]
    label_key = "summary"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    X_test = test_dataset[custom_sent_keys]

    automl = AutoML()

    automl_settings = {
        "gpu_per_trial": 0,
        "max_iter": 3,
        "time_budget": 20,
        "task": "summarization",
        "metric": "rouge1",
        "log_file_name": "seqclass.log",
    }

    automl_settings["hf_args"] = {
        "model_path": "patrickvonplaten/t5-tiny-random",
        "output_dir": "test/data/output/",
        "ckpt_per_epoch": 1,
        "fp16": False,
    }

    try:
        automl.fit(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            **automl_settings
        )
    except requests.exceptions.HTTPError:
        return
    automl = AutoML()
    automl.retrain_from_log(
        X_train=X_train,
        y_train=y_train,
        train_full=True,
        record_id=0,
        **automl_settings
    )
    automl.predict(X_test)


if __name__ == "__main__":
    test_summarization()
