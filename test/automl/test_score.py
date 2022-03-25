from flaml import AutoML
import pandas as pd
from sklearn.datasets import fetch_california_housing, fetch_openml


class TestScore:
    def test_forecast(self, budget=5):
        import pickle

        # using dataframe
        import statsmodels.api as sm

        data = sm.datasets.co2.load_pandas().data["co2"].resample("MS").mean()
        data = (
            data.fillna(data.bfill())
            .to_frame()
            .reset_index()
            .rename(columns={"index": "ds", "co2": "y"})
        )
        num_samples = data.shape[0]
        time_horizon = 12
        split_idx = num_samples - time_horizon
        X_test = data[split_idx:]["ds"]
        y_test = data[split_idx:]["y"]

        df = data[:split_idx]
        automl = AutoML()
        settings = {
            "time_budget": budget,  # total running time in seconds
            "metric": "mape",  # primary metric
            "task": "ts_forecast",  # task type
            "log_file_name": "test/CO2_forecast.log",  # flaml log file
            "eval_method": "holdout",
            "label": "y",
        }
        """The main flaml automl API"""
        try:
            import prophet

            automl.fit(
                dataframe=df,
                estimator_list=["prophet", "arima", "sarimax"],
                **settings,
                period=time_horizon,
            )
            automl.score(X_test, y_test)
            automl.pickle("automl.pkl")
            with open("automl.pkl", "rb") as f:
                pickle.load(f)
        except ImportError:
            print("not using prophet due to ImportError")
            automl.fit(
                dataframe=df,
                **settings,
                estimator_list=["arima", "sarimax"],
                period=time_horizon,
            )
            automl.score(X_test, y_test)
            automl.pickle("automl.pkl")
            with open("automl.pkl", "rb") as f:
                pickle.load(f)

    def test_classification(self):
        X = pd.DataFrame(
            {
                "f1": [1, -2, 3, -4, 5, -6, -7, 8, -9, -10, -11, -12, -13, -14],
                "f2": [
                    3.0,
                    16.0,
                    10.0,
                    12.0,
                    3.0,
                    14.0,
                    11.0,
                    12.0,
                    5.0,
                    14.0,
                    20.0,
                    16.0,
                    15.0,
                    11.0,
                ],
                "f3": [
                    "a",
                    "b",
                    "a",
                    "c",
                    "c",
                    "b",
                    "b",
                    "b",
                    "b",
                    "a",
                    "b",
                    1.0,
                    1.0,
                    "a",
                ],
                "f4": [
                    True,
                    True,
                    False,
                    True,
                    True,
                    False,
                    False,
                    False,
                    True,
                    True,
                    False,
                    False,
                    True,
                    True,
                ],
            }
        )
        y = pd.Series([0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1])

        automl = AutoML()
        for each_estimator in [
            "catboost",
            "lrl2",
            "lrl1",
            "rf",
            "lgbm",
            "extra_tree",
            "kneighbor",
            "xgboost",
        ]:
            automl_settings = {
                "time_budget": 6,
                "task": "classification",
                "n_jobs": 1,
                "estimator_list": [each_estimator],
                "metric": "accuracy",
                "log_training_metric": True,
            }
        automl.score(X, y)  # for covering the case no estimator is trained

        automl.fit(X, y, **automl_settings)
        automl.score(X, y)
        automl.score(X, y, **{"metric": "accuracy"})

        automl.pickle("automl.pkl")

    def test_regression(self):
        automl_experiment = AutoML()

        X_train, y_train = fetch_california_housing(return_X_y=True)
        n = int(len(y_train) * 9 // 10)

        for each_estimator in [
            "lgbm",
            "xgboost",
            "rf",
            "extra_tree",
            "catboost",
            "kneighbor",
        ]:
            automl_settings = {
                "time_budget": 2,
                "task": "regression",
                "log_file_name": "test/california.log",
                "log_training_metric": True,
                "estimator_list": [each_estimator],
                "n_jobs": 1,
                "model_history": True,
            }
            automl_experiment.fit(
                X_train=X_train[:n],
                y_train=y_train[:n],
                X_val=X_train[n:],
                y_val=y_train[n:],
                **automl_settings,
            )

            automl_experiment.score(X_train[n:], y_train[n:], **{"metric": "mse"})
            automl_experiment.pickle("automl.pkl")

    def test_rank(self):
        from sklearn.externals._arff import ArffException

        dataset = "credit-g"

        try:
            X, y = fetch_openml(name=dataset, return_X_y=True)
            y = y.cat.codes
        except (ArffException, ValueError):
            from sklearn.datasets import load_wine

            X, y = load_wine(return_X_y=True)

        import numpy as np

        automl = AutoML()
        n = 500

        for each_estimator in ["lgbm", "xgboost"]:
            automl_settings = {
                "time_budget": 2,
                "task": "rank",
                "log_file_name": "test/{}.log".format(dataset),
                "model_history": True,
                "groups": np.array([0] * 200 + [1] * 200 + [2] * 100),  # group labels
                "learner_selector": "roundrobin",
                "estimator_list": [each_estimator],
            }
            automl.fit(X[:n], y[:n], **automl_settings)
            try:
                automl.score(X[n:], y[n:])
                automl.pickle("automl.pkl")
            except NotImplementedError:
                pass


if __name__ == "__main__":
    test = TestScore()
    test.test_forecast()
