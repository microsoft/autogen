import pytest
from pandas import DataFrame
from sklearn.datasets import load_iris
import mlflow
import mlflow.entities
from flaml import AutoML


class TestMLFlowLoggingParam:
    def test_should_start_new_run_by_default(self, automl_settings):
        with mlflow.start_run():
            parent = mlflow.last_active_run()
            automl = AutoML()
            X_train, y_train = load_iris(return_X_y=True)
            automl.fit(X_train=X_train, y_train=y_train, **automl_settings)

        children = self._get_child_runs(parent)
        assert len(children) >= 1, "Expected at least 1 child run, got {}".format(len(children))

    def test_should_not_start_new_run_when_mlflow_logging_set_to_false_in_init(self, automl_settings):
        with mlflow.start_run():
            parent = mlflow.last_active_run()
            automl = AutoML(mlflow_logging=False)
            X_train, y_train = load_iris(return_X_y=True)
            automl.fit(X_train=X_train, y_train=y_train, **automl_settings)

        children = self._get_child_runs(parent)
        assert len(children) == 0, "Expected 0 child runs, got {}".format(len(children))

    def test_should_not_start_new_run_when_mlflow_logging_set_to_false_in_fit(self, automl_settings):
        with mlflow.start_run():
            parent = mlflow.last_active_run()
            automl = AutoML()
            X_train, y_train = load_iris(return_X_y=True)
            automl.fit(X_train=X_train, y_train=y_train, mlflow_logging=False, **automl_settings)

        children = self._get_child_runs(parent)
        assert len(children) == 0, "Expected 0 child runs, got {}".format(len(children))

    def test_should_start_new_run_when_mlflow_logging_set_to_true_in_fit(self, automl_settings):
        with mlflow.start_run():
            parent = mlflow.last_active_run()
            automl = AutoML(mlflow_logging=False)
            X_train, y_train = load_iris(return_X_y=True)
            automl.fit(X_train=X_train, y_train=y_train, mlflow_logging=True, **automl_settings)

        children = self._get_child_runs(parent)
        assert len(children) >= 1, "Expected at least 1 child run, got {}".format(len(children))

    @staticmethod
    def _get_child_runs(parent_run: mlflow.entities.Run) -> DataFrame:
        experiment_id = parent_run.info.experiment_id
        return mlflow.search_runs(
            [experiment_id], filter_string="tags.mlflow.parentRunId = '{}'".format(parent_run.info.run_id)
        )

    @pytest.fixture(scope="class")
    def automl_settings(self):
        return {
            "time_budget": 2,  # in seconds
            "metric": "accuracy",
            "task": "classification",
            "log_file_name": "iris.log",
        }
