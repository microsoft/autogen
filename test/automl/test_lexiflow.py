from flaml import AutoML
from flaml.data import load_openml_dataset


def _test_lexiflow():

    X_train, X_test, y_train, y_test = load_openml_dataset(
        dataset_id=179, data_dir="test/data"
    )

    lexico_objectives = {}
    lexico_objectives["metrics"] = ["val_loss", "pred_time"]
    lexico_objectives["tolerances"] = {"val_loss": 0.01, "pred_time": 0.0}
    lexico_objectives["targets"] = {"val_loss": 0.0, "pred_time": 0.0}
    lexico_objectives["modes"] = ["min", "min"]

    automl = AutoML()
    settings = {
        "time_budget": 100,
        "lexico_objectives": lexico_objectives,
        "estimator_list": ["xgboost"],
        "use_ray": True,
        "task": "classification",
        "max_iter": 10000000,
        "train_time_limit": 60,
        "verbose": 0,
        "eval_method": "holdout",
        "mem_thres": 128 * (1024**3),
        "seed": 1,
    }
    automl.fit(X_train=X_train, y_train=y_train, X_val=X_test, y_val=y_test, **settings)
    print(automl.predict(X_train))
    print(automl.model)
    print(automl.config_history)
    print(automl.best_iteration)
    print(automl.best_estimator)


if __name__ == "__main__":
    _test_lexiflow()
