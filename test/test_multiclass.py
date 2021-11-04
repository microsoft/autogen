import unittest
import numpy as np
import scipy.sparse
from sklearn.datasets import load_iris, load_wine


from flaml import AutoML
from flaml.data import CLASSIFICATION, get_output_from_log
from flaml.model import LGBMEstimator, XGBoostSklearnEstimator, SKLearnEstimator
from flaml import tune
from flaml.training_log import training_log_reader


class MyRegularizedGreedyForest(SKLearnEstimator):
    def __init__(self, task="binary", **config):

        super().__init__(task, **config)

        if task in CLASSIFICATION:
            from rgf.sklearn import RGFClassifier

            self.estimator_class = RGFClassifier
        else:
            from rgf.sklearn import RGFRegressor

            self.estimator_class = RGFRegressor

    @classmethod
    def search_space(cls, data_size, task):
        space = {
            "max_leaf": {
                "domain": tune.lograndint(lower=4, upper=data_size),
                "init_value": 4,
            },
            "n_iter": {
                "domain": tune.lograndint(lower=1, upper=data_size),
                "init_value": 1,
            },
            "n_tree_search": {
                "domain": tune.lograndint(lower=1, upper=32768),
                "init_value": 1,
            },
            "opt_interval": {
                "domain": tune.lograndint(lower=1, upper=10000),
                "init_value": 100,
            },
            "learning_rate": {"domain": tune.loguniform(lower=0.01, upper=20.0)},
            "min_samples_leaf": {
                "domain": tune.lograndint(lower=1, upper=20),
                "init_value": 20,
            },
        }
        return space

    @classmethod
    def size(cls, config):
        max_leaves = int(round(config["max_leaf"]))
        n_estimators = int(round(config["n_iter"]))
        return (max_leaves * 3 + (max_leaves - 1) * 4 + 1.0) * n_estimators * 8

    @classmethod
    def cost_relative2lgbm(cls):
        return 1.0


class MyLargeXGB(XGBoostSklearnEstimator):
    @classmethod
    def search_space(cls, **params):
        return {
            "n_estimators": {
                "domain": tune.lograndint(lower=4, upper=32768),
                "init_value": 32768,
                "low_cost_init_value": 4,
            },
            "max_leaves": {
                "domain": tune.lograndint(lower=4, upper=3276),
                "init_value": 3276,
                "low_cost_init_value": 4,
            },
        }


class MyLargeLGBM(LGBMEstimator):
    @classmethod
    def search_space(cls, **params):
        return {
            "n_estimators": {
                "domain": tune.lograndint(lower=4, upper=32768),
                "init_value": 32768,
                "low_cost_init_value": 4,
            },
            "num_leaves": {
                "domain": tune.lograndint(lower=4, upper=3276),
                "init_value": 3276,
                "low_cost_init_value": 4,
            },
        }


def custom_metric(
    X_test,
    y_test,
    estimator,
    labels,
    X_train,
    y_train,
    weight_test=None,
    weight_train=None,
    config=None,
    groups_test=None,
    groups_train=None,
):
    from sklearn.metrics import log_loss
    import time

    start = time.time()
    y_pred = estimator.predict_proba(X_test)
    pred_time = (time.time() - start) / len(X_test)
    test_loss = log_loss(y_test, y_pred, labels=labels, sample_weight=weight_test)
    y_pred = estimator.predict_proba(X_train)
    train_loss = log_loss(y_train, y_pred, labels=labels, sample_weight=weight_train)
    alpha = 0.5
    return test_loss * (1 + alpha) - alpha * train_loss, {
        "test_loss": test_loss,
        "train_loss": train_loss,
        "pred_time": pred_time,
    }


class TestMultiClass(unittest.TestCase):
    def test_custom_learner(self):
        automl = AutoML()
        automl.add_learner(learner_name="RGF", learner_class=MyRegularizedGreedyForest)
        X_train, y_train = load_wine(return_X_y=True)
        settings = {
            "time_budget": 8,  # total running time in seconds
            "estimator_list": ["RGF", "lgbm", "rf", "xgboost"],
            "task": "classification",  # task type
            "sample": True,  # whether to subsample training data
            "log_file_name": "test/wine.log",
            "log_training_metric": True,  # whether to log training metric
            "n_jobs": 1,
        }

        """The main flaml automl API"""
        automl.fit(X_train=X_train, y_train=y_train, **settings)
        # print the best model found for RGF
        print(automl.best_model_for_estimator("RGF"))

        MyRegularizedGreedyForest.search_space = lambda data_size, task: {}
        automl.fit(X_train=X_train, y_train=y_train, **settings)

    def test_ensemble(self):
        automl = AutoML()
        automl.add_learner(learner_name="RGF", learner_class=MyRegularizedGreedyForest)
        X_train, y_train = load_wine(return_X_y=True)
        settings = {
            "time_budget": 5,  # total running time in seconds
            "estimator_list": ["rf", "xgboost", "catboost"],
            "task": "classification",  # task type
            "sample": True,  # whether to subsample training data
            "log_file_name": "test/wine.log",
            "log_training_metric": True,  # whether to log training metric
            "ensemble": {
                "final_estimator": MyRegularizedGreedyForest(),
                "passthrough": False,
            },
            "n_jobs": 1,
        }

        """The main flaml automl API"""
        automl.fit(X_train=X_train, y_train=y_train, **settings)

    def test_dataframe(self):
        self.test_classification(True)

    def test_custom_metric(self):
        df, y = load_iris(return_X_y=True, as_frame=True)
        df["label"] = y
        automl_experiment = AutoML()
        automl_settings = {
            "dataframe": df,
            "label": "label",
            "time_budget": 5,
            "eval_method": "cv",
            "metric": custom_metric,
            "task": "classification",
            "log_file_name": "test/iris_custom.log",
            "log_training_metric": True,
            "log_type": "all",
            "n_jobs": 1,
            "model_history": True,
            "sample_weight": np.ones(len(y)),
            "pred_time_limit": 1e-5,
            "ensemble": True,
        }
        automl_experiment.fit(**automl_settings)
        print(automl_experiment.classes_)
        print(automl_experiment.model)
        print(automl_experiment.config_history)
        print(automl_experiment.model_history)
        print(automl_experiment.best_iteration)
        print(automl_experiment.best_estimator)
        automl_experiment = AutoML()
        estimator = automl_experiment.get_estimator_from_log(
            automl_settings["log_file_name"], record_id=0, task="multi"
        )
        print(estimator)
        (
            time_history,
            best_valid_loss_history,
            valid_loss_history,
            config_history,
            metric_history,
        ) = get_output_from_log(
            filename=automl_settings["log_file_name"], time_budget=6
        )
        print(metric_history)

    def test_classification(self, as_frame=False):
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 4,
            "metric": "accuracy",
            "task": "classification",
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
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
        print(automl_experiment.classes_)
        print(automl_experiment.predict(X_train)[:5])
        print(automl_experiment.model)
        print(automl_experiment.config_history)
        print(automl_experiment.model_history)
        print(automl_experiment.best_iteration)
        print(automl_experiment.best_estimator)
        del automl_settings["metric"]
        del automl_settings["model_history"]
        del automl_settings["log_training_metric"]
        automl_experiment = AutoML()
        duration = automl_experiment.retrain_from_log(
            log_file_name=automl_settings["log_file_name"],
            X_train=X_train,
            y_train=y_train,
            train_full=True,
            record_id=0,
        )
        print(duration)
        print(automl_experiment.model)
        print(automl_experiment.predict_proba(X_train)[:5])

    def test_micro_macro_f1(self):
        automl_experiment_micro = AutoML()
        automl_experiment_macro = AutoML()
        automl_settings = {
            "time_budget": 2,
            "task": "classification",
            "log_file_name": "test/micro_macro_f1.log",
            "log_training_metric": True,
            "n_jobs": 1,
            "model_history": True,
        }
        X_train, y_train = load_iris(return_X_y=True)
        automl_experiment_micro.fit(
            X_train=X_train, y_train=y_train, metric="micro_f1", **automl_settings
        )
        automl_experiment_macro.fit(
            X_train=X_train, y_train=y_train, metric="macro_f1", **automl_settings
        )
        estimator = automl_experiment_macro.model
        y_pred = estimator.predict(X_train)
        y_pred_proba = estimator.predict_proba(X_train)
        from flaml.ml import norm_confusion_matrix, multi_class_curves

        print(norm_confusion_matrix(y_train, y_pred))
        from sklearn.metrics import roc_curve, precision_recall_curve

        print(multi_class_curves(y_train, y_pred_proba, roc_curve))
        print(multi_class_curves(y_train, y_pred_proba, precision_recall_curve))

    def test_roc_auc_ovr(self):
        automl_experiment = AutoML()
        X_train, y_train = load_iris(return_X_y=True)
        automl_settings = {
            "time_budget": 1,
            "metric": "roc_auc_ovr",
            "task": "classification",
            "log_file_name": "test/roc_auc_ovr.log",
            "log_training_metric": True,
            "n_jobs": 1,
            "sample_weight": np.ones(len(y_train)),
            "eval_method": "holdout",
            "model_history": True,
        }
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)

    def test_roc_auc_ovo(self):
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 1,
            "metric": "roc_auc_ovo",
            "task": "classification",
            "log_file_name": "test/roc_auc_ovo.log",
            "log_training_metric": True,
            "n_jobs": 1,
            "model_history": True,
        }
        X_train, y_train = load_iris(return_X_y=True)
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)

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

    def _test_memory_limit(self):
        automl_experiment = AutoML()
        automl_experiment.add_learner(
            learner_name="large_lgbm", learner_class=MyLargeLGBM
        )
        automl_settings = {
            "time_budget": None,
            "task": "classification",
            "log_file_name": "test/classification_oom.log",
            "estimator_list": ["large_lgbm"],
            "log_type": "all",
            "hpo_method": "random",
        }
        X_train, y_train = load_iris(return_X_y=True, as_frame=True)

        automl_experiment.fit(
            X_train=X_train, y_train=y_train, max_iter=1, **automl_settings
        )
        print(automl_experiment.model)

    def test_time_limit(self):
        automl_experiment = AutoML()
        automl_experiment.add_learner(
            learner_name="large_lgbm", learner_class=MyLargeLGBM
        )
        automl_experiment.add_learner(
            learner_name="large_xgb", learner_class=MyLargeXGB
        )
        automl_settings = {
            "time_budget": 0.5,
            "task": "classification",
            "log_file_name": "test/classification_timeout.log",
            "estimator_list": ["catboost"],
            "log_type": "all",
            "hpo_method": "random",
        }
        X_train, y_train = load_iris(return_X_y=True, as_frame=True)
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
        print(automl_experiment.model.params)
        automl_settings["estimator_list"] = ["large_xgb"]
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
        print(automl_experiment.model)
        automl_settings["estimator_list"] = ["large_lgbm"]
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
        print(automl_experiment.model)

    def test_fit_w_starting_point(self, as_frame=True):
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 3,
            "metric": "accuracy",
            "task": "classification",
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
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
        automl_val_accuracy = 1.0 - automl_experiment.best_loss
        print("Best ML leaner:", automl_experiment.best_estimator)
        print("Best hyperparmeter config:", automl_experiment.best_config)
        print("Best accuracy on validation data: {0:.4g}".format(automl_val_accuracy))
        print(
            "Training duration of best run: {0:.4g} s".format(
                automl_experiment.best_config_train_time
            )
        )

        starting_points = automl_experiment.best_config_per_estimator
        print("starting_points", starting_points)
        automl_settings_resume = {
            "time_budget": 2,
            "metric": "accuracy",
            "task": "classification",
            "log_file_name": "test/iris_resume.log",
            "log_training_metric": True,
            "n_jobs": 1,
            "model_history": True,
            "log_type": "all",
            "starting_points": starting_points,
        }
        new_automl_experiment = AutoML()
        new_automl_experiment.fit(
            X_train=X_train, y_train=y_train, **automl_settings_resume
        )

        new_automl_val_accuracy = 1.0 - new_automl_experiment.best_loss
        print("Best ML leaner:", new_automl_experiment.best_estimator)
        print("Best hyperparmeter config:", new_automl_experiment.best_config)
        print(
            "Best accuracy on validation data: {0:.4g}".format(new_automl_val_accuracy)
        )
        print(
            "Training duration of best run: {0:.4g} s".format(
                new_automl_experiment.best_config_train_time
            )
        )

    def test_fit_w_starting_points_list(self, as_frame=True):
        automl_experiment = AutoML()
        automl_settings = {
            "time_budget": 3,
            "metric": "accuracy",
            "task": "classification",
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
        automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
        automl_val_accuracy = 1.0 - automl_experiment.best_loss
        print("Best ML leaner:", automl_experiment.best_estimator)
        print("Best hyperparmeter config:", automl_experiment.best_config)
        print("Best accuracy on validation data: {0:.4g}".format(automl_val_accuracy))
        print(
            "Training duration of best run: {0:.4g} s".format(
                automl_experiment.best_config_train_time
            )
        )

        starting_points = {}
        log_file_name = automl_settings["log_file_name"]
        with training_log_reader(log_file_name) as reader:
            for record in reader.records():
                config = record.config
                learner = record.learner
                if learner not in starting_points:
                    starting_points[learner] = []
                starting_points[learner].append(config)
        max_iter = sum([len(s) for k, s in starting_points.items()])
        automl_settings_resume = {
            "time_budget": 2,
            "metric": "accuracy",
            "task": "classification",
            "log_file_name": "test/iris_resume_all.log",
            "log_training_metric": True,
            "n_jobs": 1,
            "max_iter": max_iter,
            "model_history": True,
            "log_type": "all",
            "starting_points": starting_points,
            "append_log": True,
        }
        new_automl_experiment = AutoML()
        new_automl_experiment.fit(
            X_train=X_train, y_train=y_train, **automl_settings_resume
        )

        new_automl_val_accuracy = 1.0 - new_automl_experiment.best_loss
        # print('Best ML leaner:', new_automl_experiment.best_estimator)
        # print('Best hyperparmeter config:', new_automl_experiment.best_config)
        print(
            "Best accuracy on validation data: {0:.4g}".format(new_automl_val_accuracy)
        )
        # print('Training duration of best run: {0:.4g} s'.format(new_automl_experiment.best_config_train_time))


if __name__ == "__main__":
    unittest.main()
