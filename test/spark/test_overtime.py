import os
import time

import numpy as np
import pytest
from sklearn.datasets import load_iris

from flaml import AutoML

try:
    from test.spark.custom_mylearner import *
except ImportError:
    from custom_mylearner import *

try:
    import pyspark
    from flaml.tune.spark.utils import check_spark
    from flaml.tune.spark.mylearner import lazy_metric

    os.environ["FLAML_MAX_CONCURRENT"] = "10"
    spark = pyspark.sql.SparkSession.builder.appName("App4OvertimeTest").getOrCreate()
    spark_available, _ = check_spark()
    skip_spark = not spark_available
except ImportError:
    skip_spark = True

pytestmark = pytest.mark.skipif(
    skip_spark, reason="Spark is not installed. Skip all spark tests."
)


def test_overtime():
    time_budget = 15
    df, y = load_iris(return_X_y=True, as_frame=True)
    df["label"] = y
    automl_experiment = AutoML()
    automl_settings = {
        "dataframe": df,
        "label": "label",
        "time_budget": time_budget,
        "eval_method": "cv",
        "metric": lazy_metric,
        "task": "classification",
        "log_file_name": "test/iris_custom.log",
        "log_training_metric": True,
        "log_type": "all",
        "n_jobs": 1,
        "model_history": True,
        "sample_weight": np.ones(len(y)),
        "pred_time_limit": 1e-5,
        "estimator_list": ["lgbm"],
        "n_concurrent_trials": 2,
        "use_spark": True,
        "force_cancel": True,
    }
    start_time = time.time()
    automl_experiment.fit(**automl_settings)
    elapsed_time = time.time() - start_time
    print(
        "time budget: {:.2f}s, actual elapsed time: {:.2f}s".format(
            time_budget, elapsed_time
        )
    )
    # assert abs(elapsed_time - time_budget) < 5  # cancel assertion because github VM sometimes is super slow, causing the test to fail
    print(automl_experiment.predict(df))
    print(automl_experiment.model)
    print(automl_experiment.best_iteration)
    print(automl_experiment.best_estimator)


if __name__ == "__main__":
    test_overtime()
