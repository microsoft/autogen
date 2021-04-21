import unittest

from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
import numpy as np
from flaml.automl import AutoML
from flaml.model import XGBoostSklearnEstimator
from flaml import tune


dataset = "credit-g"


class XGBoost2D(XGBoostSklearnEstimator):

    @classmethod
    def search_space(cls, data_size, task):
        upper = min(32768, int(data_size))
        return {
            'n_estimators': {
                'domain': tune.qloguniform(lower=4, upper=upper, q=1),
                'init_value': 4,
            },
            'max_leaves': {
                'domain': tune.qloguniform(lower=4, upper=upper, q=1),
                'init_value': 4,
            },
        }


def test_simple(method=None):
    automl = AutoML()
    automl.add_learner(learner_name='XGBoost2D',
                       learner_class=XGBoost2D)

    automl_settings = {
        "estimator_list": ['XGBoost2D'],
        "task": 'classification',
        "log_file_name": f"test/xgboost2d_{dataset}_{method}.log",
        "n_jobs": 1,
        "hpo_method": method,
        "log_type": "all",
        "time_budget": 3
    }
    from sklearn.externals._arff import ArffException
    try:
        X, y = fetch_openml(name=dataset, return_X_y=True)
    except (ArffException, ValueError):
        from sklearn.datasets import load_wine
        X, y = load_wine(return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.33, random_state=42)
    automl.fit(X_train=X_train, y_train=y_train, **automl_settings)


def _test_optuna():
    test_simple(method="optuna")


def test_grid():
    test_simple(method="grid")


if __name__ == "__main__":
    unittest.main()
