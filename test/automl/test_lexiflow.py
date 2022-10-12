from flaml import AutoML
from flaml.data import load_openml_dataset


def test_lexiflow():

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
        "use_ray": False,
        "task": "classification",
        "max_iter": -1,
        "mem_thres": 128 * (1024**3),
    }
    automl.fit(X_train=X_train, y_train=y_train, X_val=X_test, y_val=y_test, **settings)


if __name__ == "__main__":
    test_lexiflow()
