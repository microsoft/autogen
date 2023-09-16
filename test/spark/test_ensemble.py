import unittest
from sklearn.datasets import load_wine
from flaml import AutoML
from flaml.tune.spark.utils import check_spark
import os

spark_available, _ = check_spark()
skip_spark = not spark_available

os.environ["FLAML_MAX_CONCURRENT"] = "2"

# To solve pylint issue, we put code for customizing mylearner in a separate file
if os.path.exists(os.path.join(os.getcwd(), "test", "spark", "custom_mylearner.py")):
    try:
        from test.spark.custom_mylearner import *
        from flaml.tune.spark.mylearner import MyRegularizedGreedyForest

        skip_my_learner = False
    except ImportError:
        skip_my_learner = True
else:
    skip_my_learner = True


class TestEnsemble(unittest.TestCase):
    def setUp(self) -> None:
        if skip_spark:
            self.skipTest("Spark is not installed. Skip all spark tests.")

    @unittest.skipIf(
        skip_my_learner,
        "Please run pytest in the root directory of FLAML, i.e., the directory that contains the setup.py file",
    )
    def test_ensemble(self):
        automl = AutoML()
        automl.add_learner(learner_name="RGF", learner_class=MyRegularizedGreedyForest)
        X_train, y_train = load_wine(return_X_y=True)
        settings = {
            "time_budget": 5,  # total running time in seconds
            "estimator_list": ["rf", "xgboost", "catboost"],
            "task": "classification",  # task type
            "sample": True,  # whether to subsample training data
            "log_file_name": "test/wine.log",
            "log_training_metric": True,  # whether to log training metric
            "ensemble": {
                "final_estimator": MyRegularizedGreedyForest(),
                "passthrough": False,
            },
            "n_jobs": 1,
            "n_concurrent_trials": 2,
            "use_spark": True,
        }
        automl.fit(X_train=X_train, y_train=y_train, **settings)


if __name__ == "__main__":
    unittest.main()
