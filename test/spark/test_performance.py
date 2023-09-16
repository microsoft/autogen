import sys
from openml.exceptions import OpenMLServerException
from requests.exceptions import ChunkedEncodingError, SSLError
from minio.error import ServerError
from flaml.tune.spark.utils import check_spark
import os
import pytest

spark_available, _ = check_spark()
skip_spark = not spark_available

pytestmark = pytest.mark.skipif(skip_spark, reason="Spark is not installed. Skip all spark tests.")

os.environ["FLAML_MAX_CONCURRENT"] = "2"


def run_automl(budget=3, dataset_format="dataframe", hpo_method=None):
    from flaml.automl.data import load_openml_dataset
    import urllib3

    performance_check_budget = 3600
    if sys.platform == "darwin" or "nt" in os.name or "3.10" not in sys.version:
        budget = 3  # revise the buget if the platform is not linux + python 3.10
    if budget >= performance_check_budget:
        max_iter = 60
        performance_check_budget = None
    else:
        max_iter = None
    try:
        X_train, X_test, y_train, y_test = load_openml_dataset(
            dataset_id=1169, data_dir="test/", dataset_format=dataset_format
        )
    except (
        OpenMLServerException,
        ChunkedEncodingError,
        urllib3.exceptions.ReadTimeoutError,
        SSLError,
        ServerError,
        Exception,
    ) as e:
        print(e)
        return

    """ import AutoML class from flaml package """
    from flaml import AutoML

    automl = AutoML()
    settings = {
        "time_budget": budget,  # total running time in seconds
        "max_iter": max_iter,  # maximum number of iterations
        "metric": "accuracy",  # primary metrics can be chosen from: ['accuracy','roc_auc','roc_auc_ovr','roc_auc_ovo','f1','log_loss','mae','mse','r2']
        "task": "classification",  # task type
        "log_file_name": "airlines_experiment.log",  # flaml log file
        "seed": 7654321,  # random seed
        "hpo_method": hpo_method,
        "log_type": "all",
        "estimator_list": [
            "lgbm",
            "xgboost",
            "xgb_limitdepth",
            "rf",
            "extra_tree",
        ],  # list of ML learners
        "eval_method": "holdout",
        "n_concurrent_trials": 2,
        "use_spark": True,
    }

    """The main flaml automl API"""
    automl.fit(X_train=X_train, y_train=y_train, **settings)

    """ retrieve best config and best learner """
    print("Best ML leaner:", automl.best_estimator)
    print("Best hyperparmeter config:", automl.best_config)
    print("Best accuracy on validation data: {0:.4g}".format(1 - automl.best_loss))
    print("Training duration of best run: {0:.4g} s".format(automl.best_config_train_time))
    print(automl.model.estimator)
    print(automl.best_config_per_estimator)
    print("time taken to find best model:", automl.time_to_find_best_model)

    """ compute predictions of testing dataset """
    y_pred = automl.predict(X_test)
    print("Predicted labels", y_pred)
    print("True labels", y_test)
    y_pred_proba = automl.predict_proba(X_test)[:, 1]
    """ compute different metric values on testing dataset """
    from flaml.automl.ml import sklearn_metric_loss_score

    accuracy = 1 - sklearn_metric_loss_score("accuracy", y_pred, y_test)
    print("accuracy", "=", accuracy)
    print("roc_auc", "=", 1 - sklearn_metric_loss_score("roc_auc", y_pred_proba, y_test))
    print("log_loss", "=", sklearn_metric_loss_score("log_loss", y_pred_proba, y_test))
    if performance_check_budget is None:
        assert accuracy >= 0.669, "the accuracy of flaml should be larger than 0.67"


def test_automl_array():
    run_automl(3, "array", "bs")


def test_automl_performance():
    run_automl(3600)


if __name__ == "__main__":
    test_automl_array()
    test_automl_performance()
