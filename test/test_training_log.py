import os
import unittest
from tempfile import TemporaryDirectory

from sklearn.datasets import fetch_california_housing

from flaml import AutoML
from flaml.training_log import training_log_reader


class TestTrainingLog(unittest.TestCase):
    def test_training_log(self, path="test_training_log.log", estimator_list="auto"):

        with TemporaryDirectory() as d:
            filename = os.path.join(d, path)

            # Run a simple job.
            automl = AutoML()
            automl_settings = {
                "time_budget": 1,
                "metric": "mse",
                "task": "regression",
                "log_file_name": filename,
                "log_training_metric": True,
                "mem_thres": 1024 * 1024,
                "n_jobs": 1,
                "model_history": True,
                "train_time_limit": 0.1,
                "verbose": 3,
                # "ensemble": True,
                "keep_search_state": True,
                "estimator_list": estimator_list,
                "model_history": True,
            }
            X_train, y_train = fetch_california_housing(return_X_y=True)
            automl.fit(X_train=X_train, y_train=y_train, **automl_settings)
            # Check if the training log file is populated.
            self.assertTrue(os.path.exists(filename))
            if automl.best_estimator:
                estimator, config = automl.best_estimator, automl.best_config
                model0 = automl.best_model_for_estimator(estimator)
                print(model0.params["n_estimators"], config)

                # train on full data with no time limit
                automl._state.time_budget = None
                model, _ = automl._state._train_with_config(estimator, config)

                # assuming estimator & config are saved and loaded as follows
                automl = AutoML()
                automl.fit(
                    X_train=X_train,
                    y_train=y_train,
                    max_iter=1,
                    task="regression",
                    estimator_list=[estimator],
                    n_jobs=1,
                    starting_points={estimator: config},
                )
                print(automl.best_config)
                # then the fitted model should be equivalent to model
                assert (
                    str(model.estimator) == str(automl.model.estimator)
                    or estimator == "xgboost"
                    and str(model.estimator.get_dump())
                    == str(automl.model.estimator.get_dump())
                    or estimator == "catboost"
                    and str(model.estimator.get_all_params())
                    == str(automl.model.estimator.get_all_params())
                )

                with training_log_reader(filename) as reader:
                    count = 0
                    for record in reader.records():
                        print(record)
                        count += 1
                    self.assertGreater(count, 0)

            automl_settings["log_file_name"] = None
            automl.fit(X_train=X_train, y_train=y_train, **automl_settings)
            automl._selected.update(None, 0)
            automl = AutoML()
            automl.fit(X_train=X_train, y_train=y_train, max_iter=0, task="regression")

    def test_illfilename(self):
        try:
            self.test_training_log("/")
        except IsADirectoryError:
            print("IsADirectoryError happens as expected in linux.")
        except PermissionError:
            print("PermissionError happens as expected in windows.")

    def test_each_estimator(self):
        self.test_training_log(estimator_list=["xgboost"])
        self.test_training_log(estimator_list=["catboost"])
        self.test_training_log(estimator_list=["extra_tree"])
        self.test_training_log(estimator_list=["rf"])
        self.test_training_log(estimator_list=["lgbm"])
