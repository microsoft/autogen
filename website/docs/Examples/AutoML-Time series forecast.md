# AutoML - Time Series Forecast

### Prerequisites

Install the [ts_forecast] option.
```bash
pip install "flaml[ts_forecast]"
```

### Univariate time series

```python
import numpy as np
from flaml import AutoML

X_train = np.arange('2014-01', '2021-01', dtype='datetime64[M]')
y_train = np.random.random(size=72)
automl = AutoML()
automl.fit(X_train=X_train[:72],  # a single column of timestamp
           y_train=y_train,  # value for each timestamp
           period=12,  # time horizon to forecast, e.g., 12 months
           task='ts_forecast', time_budget=15,  # time budget in seconds
           log_file_name="ts_forecast.log",
          )
print(automl.predict(X_train[72:]))
```

#### Sample output

```
[flaml.automl: 11-15 18:44:49] {1485} INFO - Data split method: time
INFO:flaml.automl:Data split method: time
[flaml.automl: 11-15 18:44:49] {1489} INFO - Evaluation method: cv
INFO:flaml.automl:Evaluation method: cv
[flaml.automl: 11-15 18:44:49] {1540} INFO - Minimizing error metric: mape
INFO:flaml.automl:Minimizing error metric: mape
[flaml.automl: 11-15 18:44:49] {1577} INFO - List of ML learners in AutoML Run: ['prophet', 'arima', 'sarimax']
INFO:flaml.automl:List of ML learners in AutoML Run: ['prophet', 'arima', 'sarimax']
[flaml.automl: 11-15 18:44:49] {1826} INFO - iteration 0, current learner prophet
INFO:flaml.automl:iteration 0, current learner prophet
[flaml.automl: 11-15 18:45:00] {1944} INFO - Estimated sufficient time budget=104159s. Estimated necessary time budget=104s.
INFO:flaml.automl:Estimated sufficient time budget=104159s. Estimated necessary time budget=104s.
[flaml.automl: 11-15 18:45:00] {2029} INFO -  at 10.5s,	estimator prophet's best error=1.5681,	best estimator prophet's best error=1.5681
INFO:flaml.automl: at 10.5s,	estimator prophet's best error=1.5681,	best estimator prophet's best error=1.5681
[flaml.automl: 11-15 18:45:00] {1826} INFO - iteration 1, current learner arima
INFO:flaml.automl:iteration 1, current learner arima
[flaml.automl: 11-15 18:45:00] {2029} INFO -  at 10.7s,	estimator arima's best error=2.3515,	best estimator prophet's best error=1.5681
INFO:flaml.automl: at 10.7s,	estimator arima's best error=2.3515,	best estimator prophet's best error=1.5681
[flaml.automl: 11-15 18:45:00] {1826} INFO - iteration 2, current learner arima
INFO:flaml.automl:iteration 2, current learner arima
[flaml.automl: 11-15 18:45:01] {2029} INFO -  at 11.5s,	estimator arima's best error=2.1774,	best estimator prophet's best error=1.5681
INFO:flaml.automl: at 11.5s,	estimator arima's best error=2.1774,	best estimator prophet's best error=1.5681
[flaml.automl: 11-15 18:45:01] {1826} INFO - iteration 3, current learner arima
INFO:flaml.automl:iteration 3, current learner arima
[flaml.automl: 11-15 18:45:01] {2029} INFO -  at 11.9s,	estimator arima's best error=2.1774,	best estimator prophet's best error=1.5681
INFO:flaml.automl: at 11.9s,	estimator arima's best error=2.1774,	best estimator prophet's best error=1.5681
[flaml.automl: 11-15 18:45:01] {1826} INFO - iteration 4, current learner arima
INFO:flaml.automl:iteration 4, current learner arima
[flaml.automl: 11-15 18:45:02] {2029} INFO -  at 12.9s,	estimator arima's best error=1.8560,	best estimator prophet's best error=1.5681
INFO:flaml.automl: at 12.9s,	estimator arima's best error=1.8560,	best estimator prophet's best error=1.5681
[flaml.automl: 11-15 18:45:02] {1826} INFO - iteration 5, current learner arima
INFO:flaml.automl:iteration 5, current learner arima
[flaml.automl: 11-15 18:45:04] {2029} INFO -  at 14.4s,	estimator arima's best error=1.8560,	best estimator prophet's best error=1.5681
INFO:flaml.automl: at 14.4s,	estimator arima's best error=1.8560,	best estimator prophet's best error=1.5681
[flaml.automl: 11-15 18:45:04] {1826} INFO - iteration 6, current learner sarimax
INFO:flaml.automl:iteration 6, current learner sarimax
[flaml.automl: 11-15 18:45:04] {2029} INFO -  at 14.7s,	estimator sarimax's best error=2.3515,	best estimator prophet's best error=1.5681
INFO:flaml.automl: at 14.7s,	estimator sarimax's best error=2.3515,	best estimator prophet's best error=1.5681
[flaml.automl: 11-15 18:45:04] {1826} INFO - iteration 7, current learner sarimax
INFO:flaml.automl:iteration 7, current learner sarimax
[flaml.automl: 11-15 18:45:04] {2029} INFO -  at 15.0s,	estimator sarimax's best error=1.6371,	best estimator prophet's best error=1.5681
INFO:flaml.automl: at 15.0s,	estimator sarimax's best error=1.6371,	best estimator prophet's best error=1.5681
[flaml.automl: 11-15 18:45:05] {2242} INFO - retrain prophet for 0.5s
INFO:flaml.automl:retrain prophet for 0.5s
[flaml.automl: 11-15 18:45:05] {2247} INFO - retrained model: <prophet.forecaster.Prophet object at 0x7f042ba1da50>
INFO:flaml.automl:retrained model: <prophet.forecaster.Prophet object at 0x7f042ba1da50>
[flaml.automl: 11-15 18:45:05] {1608} INFO - fit succeeded
INFO:flaml.automl:fit succeeded
[flaml.automl: 11-15 18:45:05] {1610} INFO - Time taken to find the best model: 10.450132608413696
INFO:flaml.automl:Time taken to find the best model: 10.450132608413696
0     0.384715
1     0.191349
2     0.372324
3     0.814549
4     0.269616
5     0.470667
6     0.603665
7     0.256773
8     0.408787
9     0.663065
10    0.619943
11    0.090284
Name: yhat, dtype: float64
```

### Multivariate time series

```python
import statsmodels.api as sm

data = sm.datasets.co2.load_pandas().data
# data is given in weeks, but the task is to predict monthly, so use monthly averages instead
data = data['co2'].resample('MS').mean()
data = data.fillna(data.bfill())  # makes sure there are no missing values
data = data.to_frame().reset_index()
num_samples = data.shape[0]
time_horizon = 12
split_idx = num_samples - time_horizon
train_df = data[:split_idx]  # train_df is a dataframe with two columns: timestamp and label
X_test = data[split_idx:]['index'].to_frame()  # X_test is a dataframe with dates for prediction
y_test = data[split_idx:]['co2']  # y_test is a series of the values corresponding to the dates for prediction

from flaml import AutoML

automl = AutoML()
settings = {
    "time_budget": 10,  # total running time in seconds
    "metric": 'mape',  # primary metric for validation: 'mape' is generally used for forecast tasks
    "task": 'ts_forecast',  # task type
    "log_file_name": 'CO2_forecast.log',  # flaml log file
    "eval_method": "holdout",  # validation method can be chosen from ['auto', 'holdout', 'cv']
    "seed": 7654321,  # random seed
}

automl.fit(dataframe=train_df,  # training data
           label='co2',  # label column
           period=time_horizon,  # key word argument 'period' must be included for forecast task)
           **settings)
```

#### Sample output

```
[flaml.automl: 11-15 18:54:12] {1485} INFO - Data split method: time
INFO:flaml.automl:Data split method: time
[flaml.automl: 11-15 18:54:12] {1489} INFO - Evaluation method: holdout
INFO:flaml.automl:Evaluation method: holdout
[flaml.automl: 11-15 18:54:13] {1540} INFO - Minimizing error metric: mape
INFO:flaml.automl:Minimizing error metric: mape
[flaml.automl: 11-15 18:54:13] {1577} INFO - List of ML learners in AutoML Run: ['prophet', 'arima', 'sarimax']
INFO:flaml.automl:List of ML learners in AutoML Run: ['prophet', 'arima', 'sarimax']
[flaml.automl: 11-15 18:54:13] {1826} INFO - iteration 0, current learner prophet
INFO:flaml.automl:iteration 0, current learner prophet
[flaml.automl: 11-15 18:54:15] {1944} INFO - Estimated sufficient time budget=25297s. Estimated necessary time budget=25s.
INFO:flaml.automl:Estimated sufficient time budget=25297s. Estimated necessary time budget=25s.
[flaml.automl: 11-15 18:54:15] {2029} INFO -  at 2.6s,	estimator prophet's best error=0.0008,	best estimator prophet's best error=0.0008
INFO:flaml.automl: at 2.6s,	estimator prophet's best error=0.0008,	best estimator prophet's best error=0.0008
[flaml.automl: 11-15 18:54:15] {1826} INFO - iteration 1, current learner prophet
INFO:flaml.automl:iteration 1, current learner prophet
[flaml.automl: 11-15 18:54:18] {2029} INFO -  at 5.2s,	estimator prophet's best error=0.0008,	best estimator prophet's best error=0.0008
INFO:flaml.automl: at 5.2s,	estimator prophet's best error=0.0008,	best estimator prophet's best error=0.0008
[flaml.automl: 11-15 18:54:18] {1826} INFO - iteration 2, current learner arima
INFO:flaml.automl:iteration 2, current learner arima
[flaml.automl: 11-15 18:54:18] {2029} INFO -  at 5.5s,	estimator arima's best error=0.0047,	best estimator prophet's best error=0.0008
INFO:flaml.automl: at 5.5s,	estimator arima's best error=0.0047,	best estimator prophet's best error=0.0008
[flaml.automl: 11-15 18:54:18] {1826} INFO - iteration 3, current learner arima
INFO:flaml.automl:iteration 3, current learner arima
[flaml.automl: 11-15 18:54:18] {2029} INFO -  at 5.6s,	estimator arima's best error=0.0047,	best estimator prophet's best error=0.0008
INFO:flaml.automl: at 5.6s,	estimator arima's best error=0.0047,	best estimator prophet's best error=0.0008
[flaml.automl: 11-15 18:54:18] {1826} INFO - iteration 4, current learner prophet
INFO:flaml.automl:iteration 4, current learner prophet
[flaml.automl: 11-15 18:54:21] {2029} INFO -  at 8.1s,	estimator prophet's best error=0.0005,	best estimator prophet's best error=0.0005
INFO:flaml.automl: at 8.1s,	estimator prophet's best error=0.0005,	best estimator prophet's best error=0.0005
[flaml.automl: 11-15 18:54:21] {1826} INFO - iteration 5, current learner arima
INFO:flaml.automl:iteration 5, current learner arima
[flaml.automl: 11-15 18:54:21] {2029} INFO -  at 8.9s,	estimator arima's best error=0.0047,	best estimator prophet's best error=0.0005
INFO:flaml.automl: at 8.9s,	estimator arima's best error=0.0047,	best estimator prophet's best error=0.0005
[flaml.automl: 11-15 18:54:21] {1826} INFO - iteration 6, current learner arima
INFO:flaml.automl:iteration 6, current learner arima
[flaml.automl: 11-15 18:54:22] {2029} INFO -  at 9.7s,	estimator arima's best error=0.0047,	best estimator prophet's best error=0.0005
INFO:flaml.automl: at 9.7s,	estimator arima's best error=0.0047,	best estimator prophet's best error=0.0005
[flaml.automl: 11-15 18:54:22] {1826} INFO - iteration 7, current learner sarimax
INFO:flaml.automl:iteration 7, current learner sarimax
[flaml.automl: 11-15 18:54:23] {2029} INFO -  at 10.1s,	estimator sarimax's best error=0.0047,	best estimator prophet's best error=0.0005
INFO:flaml.automl: at 10.1s,	estimator sarimax's best error=0.0047,	best estimator prophet's best error=0.0005
[flaml.automl: 11-15 18:54:23] {2242} INFO - retrain prophet for 0.9s
INFO:flaml.automl:retrain prophet for 0.9s
[flaml.automl: 11-15 18:54:23] {2247} INFO - retrained model: <prophet.forecaster.Prophet object at 0x7f0418e21f50>
INFO:flaml.automl:retrained model: <prophet.forecaster.Prophet object at 0x7f0418e21f50>
[flaml.automl: 11-15 18:54:23] {1608} INFO - fit succeeded
INFO:flaml.automl:fit succeeded
[flaml.automl: 11-15 18:54:23] {1610} INFO - Time taken to find the best model: 8.118467330932617
INFO:flaml.automl:Time taken to find the best model: 8.118467330932617
[flaml.automl: 11-15 18:54:23] {1624} WARNING - Time taken to find the best model is 81% of the provided time budget and not all estimators' hyperparameter search converged. Consider increasing the time budget.
WARNING:flaml.automl:Time taken to find the best model is 81% of the provided time budget and not all estimators' hyperparameter search converged. Consider increasing the time budget.
```

#### Compute and plot predictions

```python
flaml_y_pred = automl.predict(X_test)
import matplotlib.pyplot as plt

plt.plot(X_test, y_test, label='Actual level')
plt.plot(X_test, flaml_y_pred, label='FLAML forecast')
plt.xlabel('Date')
plt.ylabel('CO2 Levels')
plt.legend()
```

![png](images/CO2.png)

[Link to notebook](https://github.com/microsoft/FLAML/blob/main/notebook/automl_time_series_forecast.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/FLAML/blob/main/notebook/automl_time_series_forecast.ipynb)