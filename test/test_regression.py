import unittest
import numpy as np
import scipy.sparse
from sklearn.datasets import (
    fetch_california_housing,
)

from flaml import AutoML
from flaml.data import get_output_from_log
from flaml.model import XGBoostEstimator


def logregobj(preds, dtrain):
    labels = dtrain.get_label()
    preds = 1.0 / (1.0 + np.exp(-preds))  # transform raw leaf weight
    grad = preds - labels
    hess = preds * (1.0 - preds)
    return grad, hess


class MyXGB1(XGBoostEstimator):
    """XGBoostEstimator with logregobj as the objective function"""

    def __init__(self, **config):
        super().__init__(objective=logregobj, **config)


class MyXGB2(XGBoostEstimator):
    """XGBoostEstimator with 'reg:squarederror' as the objective function"""

    def __init__(self, **config):
        super().__init__(objective="reg:squarederror", **config)


class TestRegression(unittest.TestCase):
    def test_regression(self):
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 2,
            "task": "regression",
            "log_file_name": "test/california.log",
            "log_training_metric": True,
            "n_jobs": 1,
            "model_history": True,
        }
        X_train, y_train = fetch_california_housing(return_X_y=True)
        n = int(len(y_train) * 9 // 10)
        automl_experiment.fit(
            X_train=X_train[:n],
            y_train=y_train[:n],
            X_val=X_train[n:],
            y_val=y_train[n:],
            **automl_settings
        )
        assert automl_experiment._state.eval_method == "holdout"
        print(automl_experiment.predict(X_train))
        print(automl_experiment.model)
        print(automl_experiment.config_history)
        print(automl_experiment.model_history)
        print(automl_experiment.best_iteration)
        print(automl_experiment.best_estimator)
        print(get_output_from_log(automl_settings["log_file_name"], 1))
        automl_experiment.retrain_from_log(
            task="regression",
            log_file_name=automl_settings["log_file_name"],
            X_train=X_train,
            y_train=y_train,
            train_full=True,
            time_budget=1,
        )
        automl_experiment.retrain_from_log(
            task="regression",
            log_file_name=automl_settings["log_file_name"],
            X_train=X_train,
            y_train=y_train,
            train_full=True,
            time_budget=0,
        )

    def test_sparse_matrix_classification(self):
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 2,
            "metric": "auto",
            "task": "classification",
            "log_file_name": "test/sparse_classification.log",
            "split_type": "uniform",
            "n_jobs": 1,
            "model_history": True,
        }
        X_train = scipy.sparse.random(1554, 21, dtype=int)
        y_train = np.random.randint(3, size=1554)
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
        print(automl_experiment.classes_)
        print(automl_experiment.predict_proba(X_train))
        print(automl_experiment.model)
        print(automl_experiment.config_history)
        print(automl_experiment.model_history)
        print(automl_experiment.best_iteration)
        print(automl_experiment.best_estimator)

    def test_sparse_matrix_regression(self):
        X_train = scipy.sparse.random(300, 900, density=0.0001)
        y_train = np.random.uniform(size=300)
        X_val = scipy.sparse.random(100, 900, density=0.0001)
        y_val = np.random.uniform(size=100)
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 2,
            "metric": "mae",
            "task": "regression",
            "log_file_name": "test/sparse_regression.log",
            "n_jobs": 1,
            "model_history": True,
            "keep_search_state": True,
            "verbose": 0,
            "early_stop": True,
        }
        automl_experiment.fit(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            **automl_settings
        )
        assert automl_experiment._state.X_val.shape == X_val.shape
        print(automl_experiment.predict(X_train))
        print(automl_experiment.model)
        print(automl_experiment.config_history)
        print(automl_experiment.model_history)
        print(automl_experiment.best_iteration)
        print(automl_experiment.best_estimator)
        print(automl_experiment.best_config)
        print(automl_experiment.best_loss)
        print(automl_experiment.best_config_train_time)

    def test_parallel(self, hpo_method=None):
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 10,
            "task": "regression",
            "log_file_name": "test/california.log",
            "log_type": "all",
            "n_jobs": 1,
            "n_concurrent_trials": 10,
            "hpo_method": hpo_method,
        }
        X_train, y_train = fetch_california_housing(return_X_y=True)
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

    def test_sparse_matrix_regression_holdout(self):
        X_train = scipy.sparse.random(8, 100)
        y_train = np.random.uniform(size=8)
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 1,
            "eval_method": "holdout",
            "task": "regression",
            "log_file_name": "test/sparse_regression.log",
            "n_jobs": 1,
            "model_history": True,
            "metric": "mse",
            "sample_weight": np.ones(len(y_train)),
            "early_stop": True,
        }
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
        print(automl_experiment.predict(X_train))
        print(automl_experiment.model)
        print(automl_experiment.config_history)
        print(automl_experiment.model_history)
        print(automl_experiment.best_iteration)
        print(automl_experiment.best_estimator)

    def test_regression_xgboost(self):
        X_train = scipy.sparse.random(300, 900, density=0.0001)
        y_train = np.random.uniform(size=300)
        X_val = scipy.sparse.random(100, 900, density=0.0001)
        y_val = np.random.uniform(size=100)
        automl_experiment = AutoML()
        automl_experiment.add_learner(learner_name="my_xgb1", learner_class=MyXGB1)
        automl_experiment.add_learner(learner_name="my_xgb2", learner_class=MyXGB2)
        automl_settings = {
            "time_budget": 2,
            "estimator_list": ["my_xgb1", "my_xgb2"],
            "task": "regression",
            "log_file_name": "test/regression_xgboost.log",
            "n_jobs": 1,
            "model_history": True,
            "keep_search_state": True,
            "early_stop": True,
        }
        automl_experiment.fit(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            **automl_settings
        )
        assert automl_experiment._state.X_val.shape == X_val.shape
        print(automl_experiment.predict(X_train))
        print(automl_experiment.model)
        print(automl_experiment.config_history)
        print(automl_experiment.model_history)
        print(automl_experiment.best_iteration)
        print(automl_experiment.best_estimator)
        print(automl_experiment.best_config)
        print(automl_experiment.best_loss)
        print(automl_experiment.best_config_train_time)


if __name__ == "__main__":
    unittest.main()
