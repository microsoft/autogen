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
                'domain': tune.lograndint(lower=4, upper=upper),
                'low_cost_init_value': 4,
            },
            'max_leaves': {
                'domain': tune.lograndint(lower=4, upper=upper),
                'low_cost_init_value': 4,
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
        "retrain_full": "budget",
        "time_budget": 1
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
    print(automl.estimator_list)
    print(automl.search_space)
    print(automl.points_to_evaluate)
    config = automl.best_config.copy()
    config['learner'] = automl.best_estimator
    automl.trainable(config)
    from flaml import tune
    from flaml.automl import size
    from functools import partial
    analysis = tune.run(
        automl.trainable, automl.search_space, metric='val_loss', mode="min",
        low_cost_partial_config=automl.low_cost_partial_config,
        points_to_evaluate=automl.points_to_evaluate,
        cat_hp_cost=automl.cat_hp_cost,
        prune_attr=automl.prune_attr,
        min_resource=automl.min_resource,
        max_resource=automl.max_resource,
        time_budget_s=automl._state.time_budget,
        config_constraints=[(partial(size, automl._state), '<=', automl._mem_thres)],
        metric_constraints=automl.metric_constraints, num_samples=5)
    print(analysis.trials[-1])


def _test_optuna():
    test_simple(method="optuna")


def test_grid():
    test_simple(method="grid")


if __name__ == "__main__":
    unittest.main()
