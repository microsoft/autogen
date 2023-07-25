from flaml.automl.data import load_openml_dataset
from flaml import AutoML
from flaml.tune.spark.utils import check_spark
import os
import pytest

spark_available, _ = check_spark()
skip_spark = not spark_available

pytestmark = pytest.mark.skipif(skip_spark, reason="Spark is not installed. Skip all spark tests.")

os.environ["FLAML_MAX_CONCURRENT"] = "2"


def base_automl(n_concurrent_trials=1, use_ray=False, use_spark=False, verbose=0):
    from minio.error import ServerError

    try:
        X_train, X_test, y_train, y_test = load_openml_dataset(dataset_id=537, data_dir="./")
    except (ServerError, Exception):
        from sklearn.datasets import fetch_california_housing

        X_train, y_train = fetch_california_housing(return_X_y=True)
    automl = AutoML()
    settings = {
        "time_budget": 3,  # total running time in seconds
        "metric": "r2",  # primary metrics for regression can be chosen from: ['mae','mse','r2','rmse','mape']
        "estimator_list": ["lgbm", "rf", "xgboost"],  # list of ML learners
        "task": "regression",  # task type
        "log_file_name": "houses_experiment.log",  # flaml log file
        "seed": 7654321,  # random seed
        "n_concurrent_trials": n_concurrent_trials,  # the maximum number of concurrent learners
        "use_ray": use_ray,  # whether to use Ray for distributed training
        "use_spark": use_spark,  # whether to use Spark for distributed training
        "verbose": verbose,
    }

    automl.fit(X_train=X_train, y_train=y_train, **settings)

    print("Best ML leaner:", automl.best_estimator)
    print("Best hyperparmeter config:", automl.best_config)
    print("Best accuracy on validation data: {0:.4g}".format(1 - automl.best_loss))
    print("Training duration of best run: {0:.4g} s".format(automl.best_config_train_time))


def test_both_ray_spark():
    with pytest.raises(ValueError):
        base_automl(n_concurrent_trials=2, use_ray=True, use_spark=True)


def test_verboses():
    for verbose in [1, 3, 5]:
        base_automl(verbose=verbose)


def test_import_error():
    from importlib import reload
    import flaml.tune.spark.utils as utils

    reload(utils)
    utils._have_spark = False
    spark_available, spark_error_msg = utils.check_spark()
    assert not spark_available
    assert isinstance(spark_error_msg, ImportError)

    reload(utils)
    utils._spark_major_minor_version = (1, 1)
    spark_available, spark_error_msg = utils.check_spark()
    assert not spark_available
    assert isinstance(spark_error_msg, ImportError)

    reload(utils)


if __name__ == "__main__":
    base_automl()
    test_import_error()
