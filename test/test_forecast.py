def test_forecast_automl_df(budget=5):
    # using dataframe
    import statsmodels.api as sm
    data = sm.datasets.co2.load_pandas()
    data = data.data
    data = data['co2'].resample('MS').mean()
    data = data.fillna(data.bfill())
    data = data.to_frame().reset_index()
    data = data.rename(columns={'index': 'ds', 'co2': 'y'})
    num_samples = data.shape[0]
    time_horizon = 12
    split_idx = num_samples - time_horizon
    X_train = data[:split_idx]
    X_test = data[split_idx:]['ds'].to_frame()
    y_test = data[split_idx:]['y'].to_frame()
    ''' import AutoML class from flaml package '''
    from flaml import AutoML
    automl = AutoML()
    settings = {
        "time_budget": budget,  # total running time in seconds
        "metric": 'mape',  # primary metric
        "task": 'forecast',  # task type
        "log_file_name": 'CO2_forecast.log',  # flaml log file
        "eval_method": "holdout",
        "split_type": 'time'
    }
    '''The main flaml automl API'''
    try:
        automl.fit(dataframe=X_train, **settings, period=time_horizon, freq='M')
    except ImportError:
        automl.fit(dataframe=X_train, **settings, estimator_list=['arima', 'sarimax'], period=time_horizon, freq='M')
    ''' retrieve best config and best learner'''
    print('Best ML leaner:', automl.best_estimator)
    print('Best hyperparmeter config:', automl.best_config)
    print(f'Best mape on validation data: {automl.best_loss}')
    print(f'Training duration of best run: {automl.best_config_train_time}s')
    print(automl.model.estimator)
    ''' pickle and save the automl object '''
    import pickle
    with open('automl.pkl', 'wb') as f:
        pickle.dump(automl, f, pickle.HIGHEST_PROTOCOL)
    ''' compute predictions of testing dataset '''
    y_pred = automl.predict(X_test)
    print('Predicted labels', y_pred)
    print('True labels', y_test)
    ''' compute different metric values on testing dataset'''
    from flaml.ml import sklearn_metric_loss_score
    print('mape', '=', sklearn_metric_loss_score('mape', y_pred, y_test))
    from flaml.data import get_output_from_log
    time_history, best_valid_loss_history, valid_loss_history, config_history, train_loss_history = \
        get_output_from_log(filename=settings['log_file_name'], time_budget=budget)
    for config in config_history:
        print(config)
    print(automl.prune_attr)
    print(automl.max_resource)
    print(automl.min_resource)


def test_forecast_automl_Xy(budget=5):
    # using X_train and y_train
    import statsmodels.api as sm
    data = sm.datasets.co2.load_pandas()
    data = data.data
    data = data['co2'].resample('MS').mean()
    data = data.fillna(data.bfill())
    data = data.to_frame().reset_index()
    num_samples = data.shape[0]
    time_horizon = 12
    split_idx = num_samples - time_horizon
    X_train = data[:split_idx]['index'].to_frame()
    y_train = data[:split_idx]['co2']
    X_test = data[split_idx:]['index'].to_frame()
    y_test = data[split_idx:]['co2'].to_frame()
    ''' import AutoML class from flaml package '''
    from flaml import AutoML
    automl = AutoML()
    settings = {
        "time_budget": budget,  # total running time in seconds
        "metric": 'mape',  # primary metric
        "task": 'forecast',  # task type
        "log_file_name": 'CO2_forecast.log',  # flaml log file
        "eval_method": "holdout",
        "split_type": 'time'
    }
    '''The main flaml automl API'''
    try:
        automl.fit(X_train=X_train, y_train=y_train, **settings, period=time_horizon, freq='M')
    except ImportError:
        automl.fit(X_train=X_train, y_train=y_train, **settings, estimator_list=['arima', 'sarimax'], period=time_horizon, freq='M')
    ''' retrieve best config and best learner'''
    print('Best ML leaner:', automl.best_estimator)
    print('Best hyperparmeter config:', automl.best_config)
    print(f'Best mape on validation data: {automl.best_loss}')
    print(f'Training duration of best run: {automl.best_config_train_time}s')
    print(automl.model.estimator)
    ''' pickle and save the automl object '''
    import pickle
    with open('automl.pkl', 'wb') as f:
        pickle.dump(automl, f, pickle.HIGHEST_PROTOCOL)
    ''' compute predictions of testing dataset '''
    y_pred = automl.predict(X_test)
    print('Predicted labels', y_pred)
    print('True labels', y_test)
    ''' compute different metric values on testing dataset'''
    from flaml.ml import sklearn_metric_loss_score
    print('mape', '=', sklearn_metric_loss_score('mape', y_pred, y_test))
    from flaml.data import get_output_from_log
    time_history, best_valid_loss_history, valid_loss_history, config_history, train_loss_history = \
        get_output_from_log(filename=settings['log_file_name'], time_budget=budget)
    for config in config_history:
        print(config)
    print(automl.prune_attr)
    print(automl.max_resource)
    print(automl.min_resource)


if __name__ == "__main__":
    test_forecast_automl_df(60)
    test_forecast_automl_Xy(60)
