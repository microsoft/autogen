import unittest
import numpy as np
from sklearn.datasets import load_iris
from flaml import AutoML
from flaml.automl.model import LGBMEstimator
from flaml import tune


class TestWarmStart(unittest.TestCase):
    def test_fit_w_freezinghp_starting_point(self, as_frame=True):
        automl = AutoML()
        automl_settings = {
            "time_budget": 1,
            "metric": "accuracy",
            "task": "classification",
            "estimator_list": ["lgbm"],
            "log_file_name": "test/iris.log",
            "log_training_metric": True,
            "n_jobs": 1,
            "model_history": True,
        }
        X_train, y_train = load_iris(return_X_y=True, as_frame=as_frame)
        if as_frame:
            # test drop column
            X_train.columns = range(X_train.shape[1])
            X_train[X_train.shape[1]] = np.zeros(len(y_train))
        automl.fit(X_train=X_train, y_train=y_train, **automl_settings)
        automl_val_accuracy = 1.0 - automl.best_loss
        print("Best ML leaner:", automl.best_estimator)
        print("Best hyperparmeter config:", automl.best_config)
        print("Best accuracy on validation data: {0:.4g}".format(automl_val_accuracy))
        print("Training duration of best run: {0:.4g} s".format(automl.best_config_train_time))
        # 1. Get starting points from previous experiments.
        starting_points = automl.best_config_per_estimator
        print("starting_points", starting_points)
        print("loss of the starting_points", automl.best_loss_per_estimator)
        starting_point = starting_points["lgbm"]
        hps_to_freeze = ["colsample_bytree", "reg_alpha", "reg_lambda", "log_max_bin"]

        # 2. Constrct a new class:
        # a. write the hps you want to freeze as hps with constant 'domain';
        # b. specify the new search space of the other hps accrodingly.

        class MyPartiallyFreezedLargeLGBM(LGBMEstimator):
            @classmethod
            def search_space(cls, **params):
                # (1) Get the hps in the original search space
                space = LGBMEstimator.search_space(**params)
                # (2) Set up the fixed value from hps from the starting point
                for hp_name in hps_to_freeze:
                    # if an hp is specifed to be freezed, use tine value provided in the starting_point
                    # otherwise use the setting from the original search space
                    if hp_name in starting_point:
                        space[hp_name] = {"domain": starting_point[hp_name]}
                # (3.1) Configure the search space for hps that are in the original search space
                #  but you want to change something, for example the range.
                revised_hps_to_search = {
                    "n_estimators": {
                        "domain": tune.lograndint(lower=10, upper=32768),
                        "init_value": starting_point.get("n_estimators") or space["n_estimators"].get("init_value", 10),
                        "low_cost_init_value": space["n_estimators"].get("low_cost_init_value", 10),
                    },
                    "num_leaves": {
                        "domain": tune.lograndint(lower=10, upper=3276),
                        "init_value": starting_point.get("num_leaves") or space["num_leaves"].get("init_value", 10),
                        "low_cost_init_value": space["num_leaves"].get("low_cost_init_value", 10),
                    },
                    # (3.2) Add a new hp which is not in the original search space
                    "subsample": {
                        "domain": tune.uniform(lower=0.1, upper=1.0),
                        "init_value": 0.1,
                    },
                }
                space.update(revised_hps_to_search)
                return space

        new_estimator_name = "large_lgbm"
        new_automl = AutoML()
        new_automl.add_learner(learner_name=new_estimator_name, learner_class=MyPartiallyFreezedLargeLGBM)

        automl_settings_resume = {
            "time_budget": 3,
            "metric": "accuracy",
            "task": "classification",
            "estimator_list": [new_estimator_name],
            "log_file_name": "test/iris_resume.log",
            "log_training_metric": True,
            "n_jobs": 1,
            "model_history": True,
            "log_type": "all",
            "starting_points": {new_estimator_name: starting_point},
        }

        new_automl.fit(X_train=X_train, y_train=y_train, **automl_settings_resume)

        new_automl_val_accuracy = 1.0 - new_automl.best_loss
        print("Best ML leaner:", new_automl.best_estimator)
        print("Best hyperparmeter config:", new_automl.best_config)
        print("Best accuracy on validation data: {0:.4g}".format(new_automl_val_accuracy))
        print("Training duration of best run: {0:.4g} s".format(new_automl.best_config_train_time))

    def test_nobudget(self):
        automl = AutoML()
        X_train, y_train = load_iris(return_X_y=True)
        automl.fit(X_train, y_train)
        print(automl.best_config_per_estimator)

    def test_FLAML_sample_size_in_starting_points(self):
        from openml.exceptions import OpenMLServerException
        from requests.exceptions import ChunkedEncodingError, SSLError
        from minio.error import ServerError
        from flaml.automl.data import load_openml_dataset
        from flaml import AutoML

        try:
            X_train, X_test, y_train, y_test = load_openml_dataset(dataset_id=1169, data_dir="./")
        except (OpenMLServerException, ChunkedEncodingError, SSLError, ServerError, Exception):
            from sklearn.datasets import load_wine

            X_train, y_train = load_wine(return_X_y=True)

        automl_settings = {
            "time_budget": 3,
            "task": "classification",
        }

        automl1 = AutoML()
        print(len(y_train))
        automl1.fit(X_train, y_train, **automl_settings)
        print("automl1.best_config_per_estimator", automl1.best_config_per_estimator)

        automl_settings["starting_points"] = automl1.best_config_per_estimator
        automl2 = AutoML()
        automl2.fit(X_train, y_train, **automl_settings)

        automl_settings["starting_points"] = {
            "xgboost": {
                "n_estimators": 4,
                "max_leaves": 4,
                "min_child_weight": 0.26208115308159446,
                "learning_rate": 0.25912534572860507,
                "subsample": 0.9266743941610592,
                "colsample_bylevel": 1.0,
                "colsample_bytree": 1.0,
                "reg_alpha": 0.0013933617380144255,
                "reg_lambda": 0.18096917948292954,
                "FLAML_sample_size": 20000,
            },
            "xgb_limitdepth": None,
            "lrl1": None,
        }
        from flaml import tune

        automl_settings["custom_hp"] = {
            "xgboost": {
                "n_estimators": {
                    "domain": tune.choice([10, 20]),
                },
            }
        }
        automl2 = AutoML()
        automl2.fit(X_train, y_train, **automl_settings)

        try:
            import ray

            automl_settings["n_concurrent_trials"] = 2
        except ImportError:
            automl_settings["n_concurrent_trials"] = 1
        # setting different FLAML_sample_size
        automl_settings["starting_points"] = {
            "catboost": {
                "early_stopping_rounds": 10,
                "learning_rate": 0.09999999999999996,
                "n_estimators": 1,
                "FLAML_sample_size": 10000,
            },
            "xgboost": {
                "n_estimators": 4,
                "max_leaves": 4,
                "min_child_weight": 0.26208115308159446,
                "learning_rate": 0.25912534572860507,
                "subsample": 0.9266743941610592,
                "colsample_bylevel": 1.0,
                "colsample_bytree": 1.0,
                "reg_alpha": 0.0013933617380144255,
                "reg_lambda": 0.18096917948292954,
                "FLAML_sample_size": 20000,
            },
            "xgb_limitdepth": None,
            "lrl1": None,
        }
        automl3 = AutoML()
        automl3.fit(X_train, y_train, **automl_settings)

        automl_settings["sample"] = False
        automl4 = AutoML()
        try:
            automl4.fit(
                X_train,
                y_train,
                **automl_settings,
            )
            raise RuntimeError(
                "When sample=False and starting_points contain FLAML_sample_size, AssertionError is expected but not raised."
            )
        except AssertionError:
            pass


if __name__ == "__main__":
    unittest.main()
