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
        "task": "ts_forecast",  # task type
        "log_file_name": "test/CO2_forecast.log",  # flaml log file
        "eval_method": "holdout",
        "label": "y",
    }
    """The main flaml automl API"""
    try:
        import prophet

        automl.fit(dataframe=df, **settings, period=time_horizon)
    except ImportError:
        print("not using prophet due to ImportError")
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

    X_train = df[["ds"]]
    y_train = df["y"]
    automl = AutoML()
    try:
        automl.fit(X_train=X_train, y_train=y_train, **settings, period=time_horizon)
    except ImportError:
        print("not using prophet due to ImportError")
        automl.fit(
            X_train=X_train,
            y_train=y_train,
            **settings,
            estimator_list=["arima", "sarimax"],
            period=time_horizon,
        )


def test_numpy():
    X_train = np.arange("2014-01", "2021-01", dtype="datetime64[M]")
    y_train = np.random.random(size=len(X_train))
    automl = AutoML()
    try:
        import prophet

        automl.fit(
            X_train=X_train[:72],  # a single column of timestamp
            y_train=y_train[:72],  # value for each timestamp
            period=12,  # time horizon to forecast, e.g., 12 months
            task="ts_forecast",
            time_budget=3,  # time budget in seconds
            log_file_name="test/ts_forecast.log",
        )
        print(automl.predict(X_train[72:]))
    except ImportError:
        print("not using prophet due to ImportError")
        automl = AutoML()
        automl.fit(
            X_train=X_train[:72],  # a single column of timestamp
            y_train=y_train[:72],  # value for each timestamp
            period=12,  # time horizon to forecast, e.g., 12 months
            task="ts_forecast",
            time_budget=1,  # time budget in seconds
            estimator_list=["arima", "sarimax"],
            log_file_name="test/ts_forecast.log",
        )
        print(automl.predict(X_train[72:]))
        # an alternative way to specify predict steps for arima/sarimax
        print(automl.predict(12))


def load_multi_dataset():
    """multivariate time series forecasting dataset"""
    import pandas as pd

    # pd.set_option("display.max_rows", None, "display.max_columns", None)
    df = pd.read_csv("https://raw.githubusercontent.com/srivatsan88/YouTubeLI/master/dataset/nyc_energy_consumption.csv")
    # preprocessing data
    df["timeStamp"] = pd.to_datetime(df["timeStamp"])
    df = df.set_index("timeStamp")
    df = df.resample("D").mean()
    df["temp"] = df["temp"].fillna(method="ffill")
    df["precip"] = df["precip"].fillna(method="ffill")
    df = df[:-2]  # last two rows are NaN for 'demand' column so remove them
    df = df.reset_index()

    return df


def test_multivariate_forecast_num(budget=5):
    df = load_multi_dataset()
    # split data into train and test
    time_horizon = 180
    num_samples = df.shape[0]
    split_idx = num_samples - time_horizon
    train_df = df[:split_idx]
    test_df = df[split_idx:]
    X_test = test_df[["timeStamp", "temp", "precip"]]  # test dataframe must contain values for the regressors / multivariate variables
    y_test = test_df["demand"]
    # return
    automl = AutoML()
    settings = {
        "time_budget": budget,  # total running time in seconds
        "metric": "mape",  # primary metric
        "task": "ts_forecast",  # task type
        "log_file_name": "test/energy_forecast_numerical.log",  # flaml log file
        "eval_method": "holdout",
        "log_type": "all",
        "label": "demand"
    }
    '''The main flaml automl API'''
    try:
        import prophet

        automl.fit(dataframe=train_df, **settings, period=time_horizon)
    except ImportError:
        print("not using prophet due to ImportError")
        automl.fit(
            dataframe=train_df,
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

    time_history, best_valid_loss_history, valid_loss_history, config_history, metric_history = \
        get_output_from_log(filename=settings["log_file_name"], time_budget=budget)
    for config in config_history:
        print(config)
    print(automl.prune_attr)
    print(automl.max_resource)
    print(automl.min_resource)

    # import matplotlib.pyplot as plt
    #
    # plt.figure()
    # plt.plot(X_test["timeStamp"], y_test, label="Actual Demand")
    # plt.plot(X_test["timeStamp"], y_pred, label="FLAML Forecast")
    # plt.xlabel("Date")
    # plt.ylabel("Energy Demand")
    # plt.legend()
    # plt.show()


def load_multi_dataset_cat(time_horizon):
    df = load_multi_dataset()

    df = df[["timeStamp", "demand", "temp"]]

    # feature engineering - use discrete values to denote different categories
    def season(date):
        date = (date.month, date.day)
        spring = (3, 20)
        summer = (6, 21)
        fall = (9, 22)
        winter = (12, 21)
        if date < spring or date >= winter:
            return "winter"  # winter 0
        elif spring <= date < summer:
            return "spring"  # spring 1
        elif summer <= date < fall:
            return "summer"  # summer 2
        elif fall <= date < winter:
            return "fall"  # fall 3

    def get_monthly_avg(data):
        data["month"] = data["timeStamp"].dt.month
        data = data[["month", "temp"]].groupby("month")
        data = data.agg({"temp": "mean"})
        return data

    monthly_avg = get_monthly_avg(df).to_dict().get("temp")

    def above_monthly_avg(date, temp):
        month = date.month
        if temp > monthly_avg.get(month):
            return 1
        else:
            return 0

    df["season"] = df["timeStamp"].apply(season)
    df["above_monthly_avg"] = df.apply(lambda x: above_monthly_avg(x["timeStamp"], x["temp"]), axis=1)

    # split data into train and test
    num_samples = df.shape[0]
    split_idx = num_samples - time_horizon
    train_df = df[:split_idx]
    test_df = df[split_idx:]

    del train_df["temp"], train_df["month"]

    return train_df, test_df


def test_multivariate_forecast_cat(budget=5):
    time_horizon = 180
    train_df, test_df = load_multi_dataset_cat(time_horizon)
    print(train_df)
    X_test = test_df[["timeStamp", "season", "above_monthly_avg"]]  # test dataframe must contain values for the regressors / multivariate variables
    y_test = test_df["demand"]
    automl = AutoML()
    settings = {
        "time_budget": budget,  # total running time in seconds
        "metric": "mape",  # primary metric
        "task": "ts_forecast",  # task type
        "log_file_name": "test/energy_forecast_numerical.log",  # flaml log file
        "eval_method": "holdout",
        "log_type": "all",
        "label": "demand"
    }
    '''The main flaml automl API'''
    try:
        import prophet

        automl.fit(dataframe=train_df, **settings, period=time_horizon)
    except ImportError:
        print("not using prophet due to ImportError")
        automl.fit(
            dataframe=train_df,
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
    print("rmse", "=", sklearn_metric_loss_score("rmse", y_pred, y_test))
    print("mse", "=", sklearn_metric_loss_score("mse", y_pred, y_test))
    print("mae", "=", sklearn_metric_loss_score("mae", y_pred, y_test))
    from flaml.data import get_output_from_log

    time_history, best_valid_loss_history, valid_loss_history, config_history, metric_history = \
        get_output_from_log(filename=settings["log_file_name"], time_budget=budget)
    for config in config_history:
        print(config)
    print(automl.prune_attr)
    print(automl.max_resource)
    print(automl.min_resource)

    # import matplotlib.pyplot as plt
    #
    # plt.figure()
    # plt.plot(X_test["timeStamp"], y_test, label="Actual Demand")
    # plt.plot(X_test["timeStamp"], y_pred, label="FLAML Forecast")
    # plt.xlabel("Date")
    # plt.ylabel("Energy Demand")
    # plt.legend()
    # plt.show()


if __name__ == "__main__":
    test_forecast_automl(60)
    test_multivariate_forecast_num(60)
    test_multivariate_forecast_cat(60)
