import sys
import pytest
from utils import get_toy_data_seqclassification, get_automl_settings


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
        trainer = estimator._init_model_for_predict()
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

    return metrics.pop("eval_automl_metric"), metrics


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_custom_metric():
    from flaml import AutoML
    import requests

    X_train, y_train, X_val, y_val, X_test = get_toy_data_seqclassification()
    automl = AutoML()

    try:
        import ray

        if not ray.is_initialized():
            ray.init()
    except ImportError:
        return

    automl_settings = get_automl_settings()
    automl_settings["metric"] = custom_metric
    automl_settings["use_ray"] = {"local_dir": "data/output/"}

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

    # testing calling custom metric in TransformersEstimator._compute_metrics_by_dataset_name

    automl_settings["max_iter"] = 3
    automl.fit(
        X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings
    )
    automl.score(X_val, y_val, **{"metric": custom_metric})
    automl.pickle("automl.pkl")

    del automl


if __name__ == "__main__":
    test_custom_metric()
