import unittest

from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
from flaml.automl import AutoML
from flaml import tune


dataset = "credit-g"


def test_metric_constraints():
    # impose metric constrains via "pred_time_limit"
    automl = AutoML()

    automl_settings = {
        "estimator_list": ["xgboost"],
        "task": "classification",
        "log_file_name": f"test/constraints_{dataset}.log",
        "n_jobs": 1,
        "log_type": "all",
        "retrain_full": "budget",
        "keep_search_state": True,
        "time_budget": 1,
        "pred_time_limit": 5.1e-05,
    }
    from sklearn.externals._arff import ArffException

    try:
        X, y = fetch_openml(name=dataset, return_X_y=True)
    except (ArffException, ValueError):
        from sklearn.datasets import load_wine

        X, y = load_wine(return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.33, random_state=42
    )
    automl.fit(X_train=X_train, y_train=y_train, **automl_settings)
    print(automl.estimator_list)
    print(automl.search_space)
    print(automl.points_to_evaluate)
    config = automl.best_config.copy()
    config["learner"] = automl.best_estimator
    automl.trainable(config)

    from flaml.automl import size
    from functools import partial

    print("metric constraints used in automl", automl.metric_constraints)

    analysis = tune.run(
        automl.trainable,
        automl.search_space,
        metric="val_loss",
        mode="min",
        low_cost_partial_config=automl.low_cost_partial_config,
        points_to_evaluate=automl.points_to_evaluate,
        cat_hp_cost=automl.cat_hp_cost,
        resource_attr=automl.resource_attr,
        min_resource=automl.min_resource,
        max_resource=automl.max_resource,
        time_budget_s=automl._state.time_budget,
        config_constraints=[(partial(size, automl._state), "<=", automl._mem_thres)],
        metric_constraints=automl.metric_constraints,
        num_samples=5,
    )
    print(analysis.trials[-1])


def custom_metric(
    X_val,
    y_val,
    estimator,
    labels,
    X_train,
    y_train,
    weight_val,
    weight_train,
    *args,
):
    from sklearn.metrics import log_loss
    import time

    start = time.time()
    y_pred = estimator.predict_proba(X_val)
    pred_time = (time.time() - start) / len(X_val)
    val_loss = log_loss(y_val, y_pred, labels=labels, sample_weight=weight_val)
    y_pred = estimator.predict_proba(X_train)
    train_loss = log_loss(y_train, y_pred, labels=labels, sample_weight=weight_train)
    alpha = 0.5
    return val_loss * (1 + alpha) - alpha * train_loss, {
        "val_loss": val_loss,
        "val_train_loss_gap": val_loss - train_loss,
        "pred_time": pred_time,
    }


def test_metric_constraints_custom():
    automl = AutoML()
    # When you are providing a custom metric function, you can also specify constraints
    # on one or more of the metrics reported via the second object, i.e., a metrics_to_log dictionary,
    # returned by the custom metric function.
    # For example, in the following code, we add a constraint on the `pred_time` metrics and `val_train_loss_gap` metric
    # reported in `custom_metric` defined above, respectively.
    automl_settings = {
        "estimator_list": ["xgboost"],
        "task": "classification",
        "log_file_name": f"test/constraints_custom_{dataset}.log",
        "n_jobs": 1,
        "metric": custom_metric,
        "log_type": "all",
        "retrain_full": "budget",
        "keep_search_state": True,
        "time_budget": 1,
        "metric_constraints": [
            ("pred_time", "<=", 5.1e-05),
            ("val_train_loss_gap", "<=", 0.05),
        ],
    }
    from sklearn.externals._arff import ArffException

    try:
        X, y = fetch_openml(name=dataset, return_X_y=True)
    except (ArffException, ValueError):
        from sklearn.datasets import load_wine

        X, y = load_wine(return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.33, random_state=42
    )
    automl.fit(X_train=X_train, y_train=y_train, **automl_settings)
    print(automl.estimator_list)
    print(automl.search_space)
    print(automl.points_to_evaluate)
    print(
        "Best minimization objective on validation data: {0:.4g}".format(
            automl.best_loss
        )
    )
    print(
        "pred_time of the best config on validation data: {0:.4g}".format(
            automl.metrics_for_best_config[1]["pred_time"]
        )
    )
    print(
        "val_train_loss_gap of the best config on validation data: {0:.4g}".format(
            automl.metrics_for_best_config[1]["val_train_loss_gap"]
        )
    )

    config = automl.best_config.copy()
    config["learner"] = automl.best_estimator
    automl.trainable(config)

    from flaml.automl import size
    from functools import partial

    print("metric constraints in automl", automl.metric_constraints)
    analysis = tune.run(
        automl.trainable,
        automl.search_space,
        metric="val_loss",
        mode="min",
        low_cost_partial_config=automl.low_cost_partial_config,
        points_to_evaluate=automl.points_to_evaluate,
        cat_hp_cost=automl.cat_hp_cost,
        resource_attr=automl.resource_attr,
        min_resource=automl.min_resource,
        max_resource=automl.max_resource,
        time_budget_s=automl._state.time_budget,
        config_constraints=[(partial(size, automl._state), "<=", automl._mem_thres)],
        metric_constraints=automl.metric_constraints,
        num_samples=5,
    )
    print(analysis.trials[-1])


if __name__ == "__main__":
    unittest.main()
