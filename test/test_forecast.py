import numpy as np
from flaml import AutoML


def test_forecast_automl(budget=5):
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
    df = data[:split_idx]
    X_test = data[split_idx:]["ds"]
    y_test = data[split_idx:]["y"]
    automl = AutoML()
    settings = {
        "time_budget": budget,  # total running time in seconds
        "metric": "mape",  # primary metric
        "task": "forecast",  # task type
        "log_file_name": "test/CO2_forecast.log",  # flaml log file
        "eval_method": "holdout",
        "label": ("ds", "y"),
    }
    """The main flaml automl API"""
    try:
        automl.fit(dataframe=df, **settings, period=time_horizon)
    except ImportError:
        print("not using FBProphet due to ImportError")
        automl.fit(
            dataframe=df,
            **settings,
            estimator_list=["arima", "sarimax"],
            period=time_horizon,
        )
    """ retrieve best config and best learner"""
    print("Best ML leaner:", automl.best_estimator)
    print("Best hyperparmeter config:", automl.best_config)
    print(f"Best mape on validation data: {automl.best_loss}")
    print(f"Training duration of best run: {automl.best_config_train_time}s")
    print(automl.model.estimator)
    """ pickle and save the automl object """
    import pickle

    with open("automl.pkl", "wb") as f:
        pickle.dump(automl, f, pickle.HIGHEST_PROTOCOL)
    """ compute predictions of testing dataset """
    y_pred = automl.predict(X_test)
    print("Predicted labels", y_pred)
    print("True labels", y_test)
    """ compute different metric values on testing dataset"""
    from flaml.ml import sklearn_metric_loss_score

    print("mape", "=", sklearn_metric_loss_score("mape", y_pred, y_test))
    from flaml.data import get_output_from_log

    (
        time_history,
        best_valid_loss_history,
        valid_loss_history,
        config_history,
        metric_history,
    ) = get_output_from_log(filename=settings["log_file_name"], time_budget=budget)
    for config in config_history:
        print(config)
    print(automl.prune_attr)
    print(automl.max_resource)
    print(automl.min_resource)

    X_train = df["ds"]
    y_train = df["y"]
    automl = AutoML()
    try:
        automl.fit(X_train=X_train, y_train=y_train, **settings, period=time_horizon)
    except ImportError:
        print("not using FBProphet due to ImportError")
        automl.fit(
            X_train=X_train,
            y_train=y_train,
            **settings,
            estimator_list=["arima", "sarimax"],
            period=time_horizon,
        )


def test_numpy():
    X_train = np.arange("2014-01", "2021-01", dtype="datetime64[M]")
    y_train = np.random.random(size=72)
    automl = AutoML()
    try:
        automl.fit(
            X_train=X_train[:60],  # a single column of timestamp
            y_train=y_train,  # value for each timestamp
            period=12,  # time horizon to forecast, e.g., 12 months
            task="forecast",
            time_budget=3,  # time budget in seconds
            log_file_name="test/forecast.log",
        )
        print(automl.predict(X_train[60:]))
        print(automl.predict(12))
    except ValueError:
        print("ValueError for FBProphet is raised as expected.")
    except ImportError:
        print("not using FBProphet due to ImportError")
        automl = AutoML()
        automl.fit(
            X_train=X_train[:72],  # a single column of timestamp
            y_train=y_train,  # value for each timestamp
            period=12,  # time horizon to forecast, e.g., 12 months
            task="forecast",
            time_budget=1,  # time budget in seconds
            estimator_list=["arima", "sarimax"],
            log_file_name="test/forecast.log",
        )
        print(automl.predict(X_train[72:]))
        # an alternative way to specify predict steps for arima/sarimax
        print(automl.predict(12))


if __name__ == "__main__":
    test_forecast_automl(60)
