import unittest
import numpy as np
import scipy.sparse
from sklearn.datasets import load_breast_cancer
import pandas as pd
from datetime import datetime
from flaml import AutoML
from flaml.model import LGBMEstimator
from flaml import tune


class MyLargeLGBM(LGBMEstimator):
    @classmethod
    def search_space(cls, **params):
        return {
            "n_estimators": {
                "domain": tune.lograndint(lower=4, upper=32768),
                "init_value": 32768,
                "low_cost_init_value": 4,
            },
            "num_leaves": {
                "domain": tune.lograndint(lower=4, upper=32768),
                "init_value": 32768,
                "low_cost_init_value": 4,
            },
        }


class TestClassification(unittest.TestCase):
    def test_preprocess(self):
        automl = AutoML()
        X = pd.DataFrame(
            {
                "f1": [1, -2, 3, -4, 5, -6, -7, 8, -9, -10, -11, -12, -13, -14],
                "f2": [
                    3.0,
                    16.0,
                    10.0,
                    12.0,
                    3.0,
                    14.0,
                    11.0,
                    12.0,
                    5.0,
                    14.0,
                    20.0,
                    16.0,
                    15.0,
                    11.0,
                ],
                "f3": [
                    "a",
                    "b",
                    "a",
                    "c",
                    "c",
                    "b",
                    "b",
                    "b",
                    "b",
                    "a",
                    "b",
                    1.0,
                    1.0,
                    "a",
                ],
                "f4": [
                    True,
                    True,
                    False,
                    True,
                    True,
                    False,
                    False,
                    False,
                    True,
                    True,
                    False,
                    False,
                    True,
                    True,
                ],
            }
        )
        y = pd.Series([0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1])

        automl = AutoML()
        automl_settings = {
            "time_budget": 6,
            "task": "classification",
            "n_jobs": 1,
            "estimator_list": ["catboost", "lrl2"],
            "eval_method": "cv",
            "n_splits": 3,
            "metric": "accuracy",
            "log_training_metric": True,
            # "verbose": 4,
            "ensemble": True,
        }
        automl.fit(X, y, **automl_settings)

        automl = AutoML()
        automl_settings = {
            "time_budget": 2,
            "task": "classification",
            "n_jobs": 1,
            "estimator_list": ["lrl2", "kneighbor"],
            "eval_method": "cv",
            "n_splits": 3,
            "metric": "accuracy",
            "log_training_metric": True,
            "verbose": 4,
            "ensemble": True,
        }
        automl.fit(X, y, **automl_settings)

        automl = AutoML()
        automl_settings = {
            "time_budget": 3,
            "task": "classification",
            "n_jobs": 1,
            "estimator_list": ["xgboost", "catboost", "kneighbor"],
            "eval_method": "cv",
            "n_splits": 3,
            "metric": "accuracy",
            "log_training_metric": True,
            # "verbose": 4,
            "ensemble": True,
        }
        automl.fit(X, y, **automl_settings)

        automl = AutoML()
        automl_settings = {
            "time_budget": 3,
            "task": "classification",
            "n_jobs": 1,
            "estimator_list": ["lgbm", "catboost", "kneighbor"],
            "eval_method": "cv",
            "n_splits": 3,
            "metric": "accuracy",
            "log_training_metric": True,
            # "verbose": 4,
            "ensemble": True,
        }
        automl.fit(X, y, **automl_settings)

    def test_binary(self):
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 1,
            "task": "binary",
            "log_file_name": "test/breast_cancer.log",
            "log_training_metric": True,
            "n_jobs": 1,
            "model_history": True,
        }
        X_train, y_train = load_breast_cancer(return_X_y=True)
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
        _ = automl_experiment.predict(X_train)

    def test_datetime_columns(self):
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 2,
            "log_file_name": "test/datetime_columns.log",
            "log_training_metric": True,
            "n_jobs": 1,
            "model_history": True,
        }
        fake_df = pd.DataFrame(
            {
                "A": [
                    datetime(1900, 2, 3),
                    datetime(1900, 3, 4),
                    datetime(1900, 3, 4),
                    datetime(1900, 3, 4),
                    datetime(1900, 7, 2),
                    datetime(1900, 8, 9),
                ],
                "B": [
                    datetime(1900, 1, 1),
                    datetime(1900, 1, 1),
                    datetime(1900, 1, 1),
                    datetime(1900, 1, 1),
                    datetime(1900, 1, 1),
                    datetime(1900, 1, 1),
                ],
                "year_A": [
                    datetime(1900, 1, 2),
                    datetime(1900, 8, 1),
                    datetime(1900, 1, 4),
                    datetime(1900, 6, 1),
                    datetime(1900, 1, 5),
                    datetime(1900, 4, 1),
                ],
            }
        )
        y = np.array([0, 1, 0, 1, 0, 0])
        automl_experiment.fit(X_train=fake_df, y_train=y, **automl_settings)
        _ = automl_experiment.predict(fake_df)

    def test_sparse_matrix_xgboost(self):
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 3,
            "metric": "ap",
            "task": "classification",
            "log_file_name": "test/sparse_classification.log",
            "estimator_list": ["xgboost"],
            "log_type": "all",
            "n_jobs": 1,
        }
        X_train = scipy.sparse.eye(900000)
        y_train = np.random.randint(2, size=900000)
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
        print(automl_experiment.predict(X_train))
        print(automl_experiment.model)
        print(automl_experiment.config_history)
        print(automl_experiment.model_history)
        print(automl_experiment.best_iteration)
        print(automl_experiment.best_estimator)

    def test_ray_classification(self):
        from sklearn.datasets import make_classification

        X, y = make_classification(1000, 10)
        automl = AutoML()
        try:
            automl.fit(X, y, time_budget=10, task="classification", use_ray=True)
            automl.fit(
                X, y, time_budget=10, task="classification", n_concurrent_trials=2
            )
        except ImportError:
            return

    def test_parallel_xgboost(self, hpo_method=None):
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
        }
        X_train = scipy.sparse.eye(900000)
        y_train = np.random.randint(2, size=900000)
        try:
            automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
            print(automl_experiment.predict(X_train))
            print(automl_experiment.model)
            print(automl_experiment.config_history)
            print(automl_experiment.model_history)
            print(automl_experiment.best_iteration)
            print(automl_experiment.best_estimator)
        except ImportError:
            return

    def test_parallel_xgboost_others(self):
        # use random search as the hpo_method
        self.test_parallel_xgboost(hpo_method="random")

    def test_random_skip_oom(self):
        automl_experiment = AutoML()
        automl_experiment.add_learner(
            learner_name="large_lgbm", learner_class=MyLargeLGBM
        )
        automl_settings = {
            "time_budget": 2,
            "task": "classification",
            "log_file_name": "test/sparse_classification_oom.log",
            "estimator_list": ["large_lgbm"],
            "log_type": "all",
            "n_jobs": 1,
            "hpo_method": "random",
            "n_concurrent_trials": 2,
        }
        X_train = scipy.sparse.eye(900000)
        y_train = np.random.randint(2, size=900000)

        try:
            automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
            print(automl_experiment.predict(X_train))
            print(automl_experiment.model)
            print(automl_experiment.config_history)
            print(automl_experiment.model_history)
            print(automl_experiment.best_iteration)
            print(automl_experiment.best_estimator)
        except ImportError:
            print("skipping concurrency test as ray is not installed")
            return

    def test_sparse_matrix_lr(self):
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 3,
            "metric": "f1",
            "task": "classification",
            "log_file_name": "test/sparse_classification.log",
            "estimator_list": ["lrl1", "lrl2"],
            "log_type": "all",
            "n_jobs": 1,
        }
        X_train = scipy.sparse.random(3000, 3000, density=0.1)
        y_train = np.random.randint(2, size=3000)
        automl_experiment.fit(
            X_train=X_train, y_train=y_train, train_time_limit=1, **automl_settings
        )
        automl_settings["time_budget"] = 5
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
        print(automl_experiment.predict(X_train))
        print(automl_experiment.model)
        print(automl_experiment.config_history)
        print(automl_experiment.model_history)
        print(automl_experiment.best_iteration)
        print(automl_experiment.best_estimator)


if __name__ == "__main__":
    unittest.main()
