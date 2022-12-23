import numpy as np
import scipy.sparse
from flaml import AutoML
from flaml.tune.spark.utils import check_spark
import os
import pytest

# For spark, we need to put customized learner in a separate file
if os.path.exists(os.path.join(os.getcwd(), "test", "spark", "mylearner.py")):
    try:
        from test.spark.mylearner import MyLargeLGBM

        skip_my_learner = False
    except ImportError:
        skip_my_learner = True
        MyLargeLGBM = None
else:
    MyLargeLGBM = None
    skip_my_learner = True

os.environ["FLAML_MAX_CONCURRENT"] = "2"

spark_available, _ = check_spark()
skip_spark = not spark_available

pytestmark = pytest.mark.skipif(
    skip_spark, reason="Spark is not installed. Skip all spark tests."
)


def test_parallel_xgboost(hpo_method=None, data_size=1000):
    automl_experiment = AutoML()
    automl_settings = {
        "time_budget": 10,
        "metric": "ap",
        "task": "classification",
        "log_file_name": "test/sparse_classification.log",
        "estimator_list": ["xgboost"],
        "log_type": "all",
        "n_jobs": 1,
        "n_concurrent_trials": 2,
        "hpo_method": hpo_method,
        "use_spark": True,
    }
    X_train = scipy.sparse.eye(data_size)
    y_train = np.random.randint(2, size=data_size)

    automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
    print(automl_experiment.predict(X_train))
    print(automl_experiment.model)
    print(automl_experiment.config_history)
    print(automl_experiment.best_model_for_estimator("xgboost"))
    print(automl_experiment.best_iteration)
    print(automl_experiment.best_estimator)


def test_parallel_xgboost_others():
    # use random search as the hpo_method
    test_parallel_xgboost(hpo_method="random")


@pytest.mark.skip(
    reason="currently not supporting too large data, will support spark dataframe in the future"
)
def test_large_dataset():
    test_parallel_xgboost(data_size=90000000)


@pytest.mark.skipif(
    skip_my_learner,
    reason="please run pytest in the root directory of FLAML, i.e., the directory that contains the setup.py file",
)
def test_custom_learner(data_size=1000):
    automl_experiment = AutoML()
    automl_experiment.add_learner(learner_name="large_lgbm", learner_class=MyLargeLGBM)
    automl_settings = {
        "time_budget": 2,
        "task": "classification",
        "log_file_name": "test/sparse_classification_oom.log",
        "estimator_list": ["large_lgbm"],
        "log_type": "all",
        "n_jobs": 1,
        "hpo_method": "random",
        "n_concurrent_trials": 2,
        "use_spark": True,
    }
    X_train = scipy.sparse.eye(data_size)
    y_train = np.random.randint(2, size=data_size)

    automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
    print(automl_experiment.predict(X_train))
    print(automl_experiment.model)
    print(automl_experiment.config_history)
    print(automl_experiment.best_model_for_estimator("large_lgbm"))
    print(automl_experiment.best_iteration)
    print(automl_experiment.best_estimator)


if __name__ == "__main__":
    test_parallel_xgboost()
    test_parallel_xgboost_others()
    # test_large_dataset()
    if skip_my_learner:
        print(
            "please run pytest in the root directory of FLAML, i.e., the directory that contains the setup.py file"
        )
    else:
        test_custom_learner()
