import sys
import pytest


def custom_metric(
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
    from datasets import Dataset
    from flaml.model import TransformersEstimator

    if estimator._trainer is None:
        estimator._init_model_for_predict(X_test)
        trainer = estimator._trainer
        estimator._trainer = None
    else:
        trainer = estimator._trainer
    if y_test is not None:
        X_test, _ = estimator._preprocess(X_test)
        eval_dataset = Dataset.from_pandas(TransformersEstimator._join(X_test, y_test))
    else:
        X_test, _ = estimator._preprocess(X_test)
        eval_dataset = Dataset.from_pandas(X_test)

    estimator_metric_backup = estimator._metric
    estimator._metric = "rmse"
    metrics = trainer.evaluate(eval_dataset)
    estimator._metric = estimator_metric_backup

    return metrics.pop("eval_val_loss"), metrics


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_custom_metric():
    from flaml import AutoML
    import requests
    from datasets import load_dataset

    try:
        train_dataset = (
            load_dataset("glue", "mrpc", split="train").to_pandas().iloc[0:4]
        )
        dev_dataset = load_dataset("glue", "mrpc", split="train").to_pandas().iloc[0:4]
    except requests.exceptions.ConnectionError:
        return

    custom_sent_keys = ["sentence1", "sentence2"]
    label_key = "label"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    automl = AutoML()

    # testing when max_iter=1 and do retrain only without hpo

    automl_settings = {
        "gpu_per_trial": 0,
        "max_iter": 1,
        "time_budget": 5,
        "task": "seq-classification",
        "metric": custom_metric,
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

    # testing calling custom metric in TransformersEstimator._compute_metrics_by_dataset_name

    automl_settings["max_iter"] = 3
    automl.fit(
        X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings
    )

    del automl


if __name__ == "__main__":
    test_custom_metric()
