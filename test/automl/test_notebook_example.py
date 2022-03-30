import sys
from openml.exceptions import OpenMLServerException
from requests.exceptions import ChunkedEncodingError


def test_automl(budget=5, dataset_format="dataframe", hpo_method=None):
    from flaml.data import load_openml_dataset
    import urllib3

    performance_check_budget = 600
    if (
        sys.platform == "darwin"
        and budget < performance_check_budget
        and dataset_format == "dataframe"
        and "3.9" in sys.version
    ):
        budget = performance_check_budget  # revise the buget on macos
    try:
        X_train, X_test, y_train, y_test = load_openml_dataset(
            dataset_id=1169, data_dir="test/", dataset_format=dataset_format
        )
    except (
        OpenMLServerException,
        ChunkedEncodingError,
        urllib3.exceptions.ReadTimeoutError,
    ) as e:
        print(e)
        return
    """ import AutoML class from flaml package """
    from flaml import AutoML

    automl = AutoML()
    settings = {
        "time_budget": budget,  # total running time in seconds
        "metric": "accuracy",  # primary metrics can be chosen from: ['accuracy','roc_auc','roc_auc_ovr','roc_auc_ovo','f1','log_loss','mae','mse','r2']
        "task": "classification",  # task type
        "log_file_name": "airlines_experiment.log",  # flaml log file
        "seed": 7654321,  # random seed
        "hpo_method": hpo_method,
    }
    """The main flaml automl API"""
    automl.fit(X_train=X_train, y_train=y_train, **settings)
    """ retrieve best config and best learner """
    print("Best ML leaner:", automl.best_estimator)
    print("Best hyperparmeter config:", automl.best_config)
    print("Best accuracy on validation data: {0:.4g}".format(1 - automl.best_loss))
    print(
        "Training duration of best run: {0:.4g} s".format(automl.best_config_train_time)
    )
    print(automl.model.estimator)
    print("time taken to find best model:", automl.time_to_find_best_model)
    """ pickle and save the automl object """
    import pickle

    with open("automl.pkl", "wb") as f:
        pickle.dump(automl, f, pickle.HIGHEST_PROTOCOL)
    """ compute predictions of testing dataset """
    y_pred = automl.predict(X_test)
    print("Predicted labels", y_pred)
    print("True labels", y_test)
    y_pred_proba = automl.predict_proba(X_test)[:, 1]
    """ compute different metric values on testing dataset """
    from flaml.ml import sklearn_metric_loss_score

    accuracy = 1 - sklearn_metric_loss_score("accuracy", y_pred, y_test)
    print("accuracy", "=", accuracy)
    print(
        "roc_auc", "=", 1 - sklearn_metric_loss_score("roc_auc", y_pred_proba, y_test)
    )
    print("log_loss", "=", sklearn_metric_loss_score("log_loss", y_pred_proba, y_test))
    if budget >= performance_check_budget:
        assert accuracy >= 0.669, "the accuracy of flaml should be larger than 0.67"
    from flaml.data import get_output_from_log

    (
        time_history,
        best_valid_loss_history,
        valid_loss_history,
        config_history,
        metric_history,
    ) = get_output_from_log(filename=settings["log_file_name"], time_budget=6)
    for config in config_history:
        print(config)
    print(automl.resource_attr)
    print(automl.max_resource)
    print(automl.min_resource)
    if budget < performance_check_budget:
        automl.fit(X_train=X_train, y_train=y_train, ensemble=True, **settings)


def test_automl_array():
    test_automl(5, "array", "bs")


def test_mlflow():
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "mlflow"])
    import mlflow
    from flaml.data import load_openml_task

    try:
        X_train, X_test, y_train, y_test = load_openml_task(
            task_id=7592, data_dir="test/"
        )
    except (OpenMLServerException, ChunkedEncodingError) as e:
        print(e)
        return
    """ import AutoML class from flaml package """
    from flaml import AutoML

    automl = AutoML()
    settings = {
        "time_budget": 5,  # total running time in seconds
        "metric": "accuracy",  # primary metrics can be chosen from: ['accuracy','roc_auc','roc_auc_ovr','roc_auc_ovo','f1','log_loss','mae','mse','r2']
        "estimator_list": ["lgbm", "rf", "xgboost"],  # list of ML learners
        "task": "classification",  # task type
        "sample": False,  # whether to subsample training data
        "log_file_name": "adult.log",  # flaml log file
    }
    mlflow.set_experiment("flaml")
    with mlflow.start_run() as run:
        automl.fit(X_train=X_train, y_train=y_train, **settings)
        mlflow.sklearn.log_model(automl, "automl")
    loaded_model = mlflow.pyfunc.load_model(f"{run.info.artifact_uri}/automl")
    print(loaded_model.predict(X_test))
    automl._mem_thres = 0
    print(automl.trainable(automl.points_to_evaluate[0]))

    settings["use_ray"] = True
    try:
        with mlflow.start_run() as run:
            automl.fit(X_train=X_train, y_train=y_train, **settings)
            mlflow.sklearn.log_model(automl, "automl")
        automl = mlflow.sklearn.load_model(f"{run.info.artifact_uri}/automl")
        print(automl.predict_proba(X_test))
    except ImportError:
        pass
    # subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "mlflow"])


if __name__ == "__main__":
    test_automl(600)
