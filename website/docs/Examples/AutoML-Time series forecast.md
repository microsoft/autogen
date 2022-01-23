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

X_train = np.arange('2014-01', '2022-01', dtype='datetime64[M]')
y_train = np.random.random(size=84)
automl = AutoML()
automl.fit(X_train=X_train[:84],  # a single column of timestamp
           y_train=y_train,  # value for each timestamp
           period=12,  # time horizon to forecast, e.g., 12 months
           task='ts_forecast', time_budget=15,  # time budget in seconds
           log_file_name="ts_forecast.log",
           eval_method="holdout",
          )
print(automl.predict(X_train[84:]))
```

#### Sample output

```python
[flaml.automl: 01-21 08:01:20] {2018} INFO - task = ts_forecast
[flaml.automl: 01-21 08:01:20] {2020} INFO - Data split method: time
[flaml.automl: 01-21 08:01:20] {2024} INFO - Evaluation method: holdout
[flaml.automl: 01-21 08:01:20] {2124} INFO - Minimizing error metric: mape
[flaml.automl: 01-21 08:01:21] {2181} INFO - List of ML learners in AutoML Run: ['lgbm', 'rf', 'xgboost', 'extra_tree', 'xgb_limitdepth', 'prophet', 'arima', 'sarimax']
[flaml.automl: 01-21 08:01:21] {2434} INFO - iteration 0, current learner lgbm
[flaml.automl: 01-21 08:01:21] {2547} INFO - Estimated sufficient time budget=1429s. Estimated necessary time budget=1s.
[flaml.automl: 01-21 08:01:21] {2594} INFO -  at 0.9s,  estimator lgbm's best error=0.9811,     best estimator lgbm's best error=0.9811
[flaml.automl: 01-21 08:01:21] {2434} INFO - iteration 1, current learner lgbm
[flaml.automl: 01-21 08:01:21] {2594} INFO -  at 0.9s,  estimator lgbm's best error=0.9811,     best estimator lgbm's best error=0.9811
[flaml.automl: 01-21 08:01:21] {2434} INFO - iteration 2, current learner lgbm
[flaml.automl: 01-21 08:01:21] {2594} INFO -  at 0.9s,  estimator lgbm's best error=0.9811,     best estimator lgbm's best error=0.9811
[flaml.automl: 01-21 08:01:21] {2434} INFO - iteration 3, current learner lgbm
[flaml.automl: 01-21 08:01:21] {2594} INFO -  at 1.0s,  estimator lgbm's best error=0.9811,     best estimator lgbm's best error=0.9811
[flaml.automl: 01-21 08:01:21] {2434} INFO - iteration 4, current learner lgbm
[flaml.automl: 01-21 08:01:21] {2594} INFO -  at 1.0s,  estimator lgbm's best error=0.9811,     best estimator lgbm's best error=0.9811
[flaml.automl: 01-21 08:01:21] {2434} INFO - iteration 5, current learner lgbm
[flaml.automl: 01-21 08:01:21] {2594} INFO -  at 1.0s,  estimator lgbm's best error=0.9811,     best estimator lgbm's best error=0.9811
[flaml.automl: 01-21 08:01:21] {2434} INFO - iteration 6, current learner lgbm
[flaml.automl: 01-21 08:01:21] {2594} INFO -  at 1.0s,  estimator lgbm's best error=0.9652,     best estimator lgbm's best error=0.9652
[flaml.automl: 01-21 08:01:21] {2434} INFO - iteration 7, current learner lgbm
[flaml.automl: 01-21 08:01:21] {2594} INFO -  at 1.0s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:21] {2434} INFO - iteration 8, current learner lgbm
[flaml.automl: 01-21 08:01:21] {2594} INFO -  at 1.0s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:21] {2434} INFO - iteration 9, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.1s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 10, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.1s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 11, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.1s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 12, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.1s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 13, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.1s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 14, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.1s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 15, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.2s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 16, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.2s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 17, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.2s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 18, current learner rf
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.2s,  estimator rf's best error=1.0994,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 19, current learner rf
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.2s,  estimator rf's best error=1.0848,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 20, current learner xgboost
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.3s,  estimator xgboost's best error=1.0271,  best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 21, current learner rf
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.3s,  estimator rf's best error=1.0848,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 22, current learner xgboost
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.3s,  estimator xgboost's best error=1.0015,  best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 23, current learner xgboost
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.3s,  estimator xgboost's best error=1.0015,  best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 24, current learner xgboost
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.3s,  estimator xgboost's best error=1.0015,  best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 25, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.3s,  estimator extra_tree's best error=1.0130,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 26, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.4s,  estimator extra_tree's best error=1.0130,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 27, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.4s,  estimator extra_tree's best error=1.0130,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 28, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.4s,  estimator extra_tree's best error=1.0130,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 29, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.4s,  estimator extra_tree's best error=0.9499,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 30, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.5s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 31, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.5s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 32, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.5s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 33, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.5s,  estimator extra_tree's best error=0.9499,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 34, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.5s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 35, current learner xgboost
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.5s,  estimator xgboost's best error=1.0015,  best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 36, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.6s,  estimator extra_tree's best error=0.9499,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 37, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.6s,  estimator extra_tree's best error=0.9499,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 38, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.6s,  estimator extra_tree's best error=0.9499,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 39, current learner xgboost
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.6s,  estimator xgboost's best error=1.0015,  best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 40, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.6s,  estimator extra_tree's best error=0.9499,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 41, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.7s,  estimator extra_tree's best error=0.9499,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 42, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.7s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 43, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.7s,  estimator extra_tree's best error=0.9499,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 44, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.7s,  estimator xgb_limitdepth's best error=1.5815,   best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 45, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.8s,  estimator xgb_limitdepth's best error=0.9683,   best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 46, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.8s,  estimator xgb_limitdepth's best error=0.9683,   best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 47, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.8s,  estimator xgb_limitdepth's best error=0.9683,   best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 48, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.9s,  estimator xgb_limitdepth's best error=0.9683,   best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 49, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.9s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 50, current learner extra_tree
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.9s,  estimator extra_tree's best error=0.9499,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 51, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 1.9s,  estimator xgb_limitdepth's best error=0.9683,   best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 52, current learner xgboost
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 2.0s,  estimator xgboost's best error=1.0015,  best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 53, current learner xgboost
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 2.0s,  estimator xgboost's best error=1.0015,  best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 54, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 2.0s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 55, current learner lgbm
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 2.0s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 56, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 2.0s,  estimator xgb_limitdepth's best error=0.9683,   best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 57, current learner rf
[flaml.automl: 01-21 08:01:22] {2594} INFO -  at 2.0s,  estimator rf's best error=1.0848,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:22] {2434} INFO - iteration 58, current learner xgboost
[flaml.automl: 01-21 08:01:23] {2594} INFO -  at 2.1s,  estimator xgboost's best error=1.0015,  best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:23] {2434} INFO - iteration 59, current learner extra_tree
[flaml.automl: 01-21 08:01:23] {2594} INFO -  at 2.1s,  estimator extra_tree's best error=0.9499,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:23] {2434} INFO - iteration 60, current learner lgbm
[flaml.automl: 01-21 08:01:23] {2594} INFO -  at 2.1s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:23] {2434} INFO - iteration 61, current learner extra_tree
[flaml.automl: 01-21 08:01:23] {2594} INFO -  at 2.1s,  estimator extra_tree's best error=0.9499,       best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:23] {2434} INFO - iteration 62, current learner lgbm
[flaml.automl: 01-21 08:01:23] {2594} INFO -  at 2.1s,  estimator lgbm's best error=0.9466,     best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:23] {2434} INFO - iteration 63, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:23] {2594} INFO -  at 2.2s,  estimator xgb_limitdepth's best error=0.9683,   best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:23] {2434} INFO - iteration 64, current learner prophet
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.2s,  estimator prophet's best error=1.5706,  best estimator lgbm's best error=0.9466
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 65, current learner arima
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.2s,  estimator arima's best error=0.5693,    best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 66, current learner arima
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.4s,  estimator arima's best error=0.5693,    best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 67, current learner sarimax
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.4s,  estimator sarimax's best error=0.5693,  best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 68, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.5s,  estimator xgb_limitdepth's best error=0.9683,   best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 69, current learner sarimax
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.6s,  estimator sarimax's best error=0.5693,  best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 70, current learner sarimax
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.6s,  estimator sarimax's best error=0.5693,  best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 71, current learner arima
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.6s,  estimator arima's best error=0.5693,    best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 72, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.6s,  estimator xgb_limitdepth's best error=0.9683,   best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 73, current learner arima
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.7s,  estimator arima's best error=0.5693,    best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 74, current learner sarimax
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.7s,  estimator sarimax's best error=0.5693,  best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 75, current learner arima
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.8s,  estimator arima's best error=0.5693,    best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 76, current learner sarimax
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 4.9s,  estimator sarimax's best error=0.5693,  best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 77, current learner arima
[flaml.automl: 01-21 08:01:25] {2594} INFO -  at 5.0s,  estimator arima's best error=0.5693,    best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:25] {2434} INFO - iteration 78, current learner sarimax
[flaml.automl: 01-21 08:01:26] {2594} INFO -  at 5.1s,  estimator sarimax's best error=0.5693,  best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:26] {2434} INFO - iteration 79, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:26] {2594} INFO -  at 5.1s,  estimator xgb_limitdepth's best error=0.9683,   best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:26] {2434} INFO - iteration 80, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:26] {2594} INFO -  at 5.1s,  estimator xgb_limitdepth's best error=0.9683,   best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:26] {2434} INFO - iteration 81, current learner sarimax
[flaml.automl: 01-21 08:01:26] {2594} INFO -  at 5.1s,  estimator sarimax's best error=0.5693,  best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:26] {2434} INFO - iteration 82, current learner prophet
[flaml.automl: 01-21 08:01:27] {2594} INFO -  at 6.6s,  estimator prophet's best error=1.4076,  best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:27] {2434} INFO - iteration 83, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:27] {2594} INFO -  at 6.6s,  estimator xgb_limitdepth's best error=0.9683,   best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:27] {2434} INFO - iteration 84, current learner sarimax
[flaml.automl: 01-21 08:01:27] {2594} INFO -  at 6.6s,  estimator sarimax's best error=0.5693,  best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:27] {2434} INFO - iteration 85, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:27] {2594} INFO -  at 6.6s,  estimator xgb_limitdepth's best error=0.9683,   best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:27] {2434} INFO - iteration 86, current learner sarimax
[flaml.automl: 01-21 08:01:27] {2594} INFO -  at 6.8s,  estimator sarimax's best error=0.5693,  best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:27] {2434} INFO - iteration 87, current learner arima
[flaml.automl: 01-21 08:01:27] {2594} INFO -  at 6.8s,  estimator arima's best error=0.5693,    best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:27] {2434} INFO - iteration 88, current learner sarimax
[flaml.automl: 01-21 08:01:27] {2594} INFO -  at 6.9s,  estimator sarimax's best error=0.5693,  best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:27] {2434} INFO - iteration 89, current learner arima
[flaml.automl: 01-21 08:01:27] {2594} INFO -  at 6.9s,  estimator arima's best error=0.5693,    best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:27] {2434} INFO - iteration 90, current learner arima
[flaml.automl: 01-21 08:01:27] {2594} INFO -  at 7.0s,  estimator arima's best error=0.5693,    best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:27] {2434} INFO - iteration 91, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:27] {2594} INFO -  at 7.0s,  estimator xgb_limitdepth's best error=0.9683,   best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:27] {2434} INFO - iteration 92, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:27] {2594} INFO -  at 7.0s,  estimator xgb_limitdepth's best error=0.9683,   best estimator arima's best error=0.5693
[flaml.automl: 01-21 08:01:27] {2434} INFO - iteration 93, current learner sarimax
[flaml.automl: 01-21 08:01:28] {2594} INFO -  at 7.0s,  estimator sarimax's best error=0.5600,  best estimator sarimax's best error=0.5600
[flaml.automl: 01-21 08:01:28] {2434} INFO - iteration 94, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:28] {2594} INFO -  at 7.1s,  estimator xgb_limitdepth's best error=0.9683,   best estimator sarimax's best error=0.5600
[flaml.automl: 01-21 08:01:28] {2434} INFO - iteration 95, current learner sarimax
[flaml.automl: 01-21 08:01:28] {2594} INFO -  at 7.2s,  estimator sarimax's best error=0.5600,  best estimator sarimax's best error=0.5600
[flaml.automl: 01-21 08:01:28] {2434} INFO - iteration 96, current learner arima
[flaml.automl: 01-21 08:01:28] {2594} INFO -  at 7.2s,  estimator arima's best error=0.5693,    best estimator sarimax's best error=0.5600
[flaml.automl: 01-21 08:01:28] {2434} INFO - iteration 97, current learner arima
[flaml.automl: 01-21 08:01:28] {2594} INFO -  at 7.2s,  estimator arima's best error=0.5693,    best estimator sarimax's best error=0.5600
[flaml.automl: 01-21 08:01:28] {2434} INFO - iteration 98, current learner extra_tree
[flaml.automl: 01-21 08:01:28] {2594} INFO -  at 7.3s,  estimator extra_tree's best error=0.9499,       best estimator sarimax's best error=0.5600
[flaml.automl: 01-21 08:01:28] {2434} INFO - iteration 99, current learner sarimax
[flaml.automl: 01-21 08:01:28] {2594} INFO -  at 7.3s,  estimator sarimax's best error=0.5600,  best estimator sarimax's best error=0.5600
[flaml.automl: 01-21 08:01:28] {2434} INFO - iteration 100, current learner xgb_limitdepth
[flaml.automl: 01-21 08:01:28] {2594} INFO -  at 7.3s,  estimator xgb_limitdepth's best error=0.9683,   best estimator sarimax's best error=0.5600
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
[flaml.automl: 01-21 07:54:04] {2018} INFO - task = ts_forecast
[flaml.automl: 01-21 07:54:04] {2020} INFO - Data split method: time
[flaml.automl: 01-21 07:54:04] {2024} INFO - Evaluation method: holdout
[flaml.automl: 01-21 07:54:04] {2124} INFO - Minimizing error metric: mape
Importing plotly failed. Interactive plots will not work.
[flaml.automl: 01-21 07:54:04] {2181} INFO - List of ML learners in AutoML Run: ['lgbm', 'rf', 'xgboost', 'extra_tree', 'xgb_limitdepth', 'prophet', 'arima', 'sarimax']
[flaml.automl: 01-21 07:54:04] {2434} INFO - iteration 0, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2547} INFO - Estimated sufficient time budget=2145s. Estimated necessary time budget=2s.
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 0.9s,  estimator lgbm's best error=0.0621,     best estimator lgbm's best error=0.0621
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 1, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.0s,  estimator lgbm's best error=0.0574,     best estimator lgbm's best error=0.0574
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 2, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.0s,  estimator lgbm's best error=0.0464,     best estimator lgbm's best error=0.0464
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 3, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.0s,  estimator lgbm's best error=0.0464,     best estimator lgbm's best error=0.0464
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 4, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.0s,  estimator lgbm's best error=0.0365,     best estimator lgbm's best error=0.0365
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 5, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.1s,  estimator lgbm's best error=0.0192,     best estimator lgbm's best error=0.0192
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 6, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.1s,  estimator lgbm's best error=0.0192,     best estimator lgbm's best error=0.0192
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 7, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.1s,  estimator lgbm's best error=0.0192,     best estimator lgbm's best error=0.0192
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 8, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.2s,  estimator lgbm's best error=0.0110,     best estimator lgbm's best error=0.0110
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 9, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.2s,  estimator lgbm's best error=0.0110,     best estimator lgbm's best error=0.0110
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 10, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.2s,  estimator lgbm's best error=0.0036,     best estimator lgbm's best error=0.0036
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 11, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.4s,  estimator lgbm's best error=0.0023,     best estimator lgbm's best error=0.0023
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 12, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.4s,  estimator lgbm's best error=0.0023,     best estimator lgbm's best error=0.0023
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 13, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.5s,  estimator lgbm's best error=0.0021,     best estimator lgbm's best error=0.0021
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 14, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.6s,  estimator lgbm's best error=0.0021,     best estimator lgbm's best error=0.0021
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 15, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.7s,  estimator lgbm's best error=0.0020,     best estimator lgbm's best error=0.0020
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 16, current learner lgbm
[flaml.automl: 01-21 07:54:05] {2594} INFO -  at 1.8s,  estimator lgbm's best error=0.0017,     best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:05] {2434} INFO - iteration 17, current learner lgbm
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 1.9s,  estimator lgbm's best error=0.0017,     best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 18, current learner lgbm
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.0s,  estimator lgbm's best error=0.0017,     best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 19, current learner lgbm
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.1s,  estimator lgbm's best error=0.0017,     best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 20, current learner rf
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.1s,  estimator rf's best error=0.0228,       best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 21, current learner rf
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.1s,  estimator rf's best error=0.0210,       best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 22, current learner xgboost
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.2s,  estimator xgboost's best error=0.6738,  best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 23, current learner xgboost
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.2s,  estimator xgboost's best error=0.6738,  best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 24, current learner xgboost
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.2s,  estimator xgboost's best error=0.1717,  best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 25, current learner xgboost
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.3s,  estimator xgboost's best error=0.0249,  best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 26, current learner xgboost
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.3s,  estimator xgboost's best error=0.0249,  best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 27, current learner xgboost
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.3s,  estimator xgboost's best error=0.0242,  best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 28, current learner extra_tree
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.4s,  estimator extra_tree's best error=0.0245,       best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 29, current learner extra_tree
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.4s,  estimator extra_tree's best error=0.0160,       best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 30, current learner lgbm
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.5s,  estimator lgbm's best error=0.0017,     best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 31, current learner lgbm
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.6s,  estimator lgbm's best error=0.0017,     best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 32, current learner rf
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.6s,  estimator rf's best error=0.0210,       best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 33, current learner extra_tree
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.6s,  estimator extra_tree's best error=0.0160,       best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 34, current learner lgbm
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.8s,  estimator lgbm's best error=0.0017,     best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 35, current learner extra_tree
[flaml.automl: 01-21 07:54:06] {2594} INFO -  at 2.8s,  estimator extra_tree's best error=0.0158,       best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:06] {2434} INFO - iteration 36, current learner xgb_limitdepth
[flaml.automl: 01-21 07:54:07] {2594} INFO -  at 2.8s,  estimator xgb_limitdepth's best error=0.0447,   best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:07] {2434} INFO - iteration 37, current learner xgb_limitdepth
[flaml.automl: 01-21 07:54:07] {2594} INFO -  at 2.9s,  estimator xgb_limitdepth's best error=0.0447,   best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:07] {2434} INFO - iteration 38, current learner xgb_limitdepth
[flaml.automl: 01-21 07:54:07] {2594} INFO -  at 2.9s,  estimator xgb_limitdepth's best error=0.0029,   best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:07] {2434} INFO - iteration 39, current learner xgb_limitdepth
[flaml.automl: 01-21 07:54:07] {2594} INFO -  at 3.0s,  estimator xgb_limitdepth's best error=0.0018,   best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:07] {2434} INFO - iteration 40, current learner xgb_limitdepth
[flaml.automl: 01-21 07:54:07] {2594} INFO -  at 3.1s,  estimator xgb_limitdepth's best error=0.0018,   best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:07] {2434} INFO - iteration 41, current learner xgb_limitdepth
[flaml.automl: 01-21 07:54:07] {2594} INFO -  at 3.1s,  estimator xgb_limitdepth's best error=0.0018,   best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:07] {2434} INFO - iteration 42, current learner xgb_limitdepth
[flaml.automl: 01-21 07:54:07] {2594} INFO -  at 3.3s,  estimator xgb_limitdepth's best error=0.0018,   best estimator lgbm's best error=0.0017
[flaml.automl: 01-21 07:54:07] {2434} INFO - iteration 43, current learner prophet
[flaml.automl: 01-21 07:54:09] {2594} INFO -  at 5.5s,  estimator prophet's best error=0.0008,  best estimator prophet's best error=0.0008
[flaml.automl: 01-21 07:54:09] {2434} INFO - iteration 44, current learner arima
[flaml.automl: 01-21 07:54:10] {2594} INFO -  at 6.1s,  estimator arima's best error=0.0047,    best estimator prophet's best error=0.0008
[flaml.automl: 01-21 07:54:10] {2434} INFO - iteration 45, current learner sarimax
[flaml.automl: 01-21 07:54:10] {2594} INFO -  at 6.4s,  estimator sarimax's best error=0.0047,  best estimator prophet's best error=0.0008
[flaml.automl: 01-21 07:54:10] {2434} INFO - iteration 46, current learner lgbm
[flaml.automl: 01-21 07:54:10] {2594} INFO -  at 6.5s,  estimator lgbm's best error=0.0017,     best estimator prophet's best error=0.0008
[flaml.automl: 01-21 07:54:10] {2434} INFO - iteration 47, current learner sarimax
[flaml.automl: 01-21 07:54:10] {2594} INFO -  at 6.6s,  estimator sarimax's best error=0.0047,  best estimator prophet's best error=0.0008
[flaml.automl: 01-21 07:54:10] {2434} INFO - iteration 48, current learner sarimax
[flaml.automl: 01-21 07:54:11] {2594} INFO -  at 6.9s,  estimator sarimax's best error=0.0047,  best estimator prophet's best error=0.0008
[flaml.automl: 01-21 07:54:11] {2434} INFO - iteration 49, current learner arima
[flaml.automl: 01-21 07:54:11] {2594} INFO -  at 6.9s,  estimator arima's best error=0.0047,    best estimator prophet's best error=0.0008
[flaml.automl: 01-21 07:54:11] {2434} INFO - iteration 50, current learner xgb_limitdepth
[flaml.automl: 01-21 07:54:11] {2594} INFO -  at 7.0s,  estimator xgb_limitdepth's best error=0.0018,   best estimator prophet's best error=0.0008
[flaml.automl: 01-21 07:54:11] {2434} INFO - iteration 51, current learner sarimax
[flaml.automl: 01-21 07:54:11] {2594} INFO -  at 7.5s,  estimator sarimax's best error=0.0047,  best estimator prophet's best error=0.0008
[flaml.automl: 01-21 07:54:11] {2434} INFO - iteration 52, current learner xgboost
[flaml.automl: 01-21 07:54:11] {2594} INFO -  at 7.6s,  estimator xgboost's best error=0.0242,  best estimator prophet's best error=0.0008
[flaml.automl: 01-21 07:54:11] {2434} INFO - iteration 53, current learner prophet
[flaml.automl: 01-21 07:54:13] {2594} INFO -  at 9.3s,  estimator prophet's best error=0.0005,  best estimator prophet's best error=0.0005
[flaml.automl: 01-21 07:54:13] {2434} INFO - iteration 54, current learner sarimax
[flaml.automl: 01-21 07:54:13] {2594} INFO -  at 9.4s,  estimator sarimax's best error=0.0047,  best estimator prophet's best error=0.0005
[flaml.automl: 01-21 07:54:13] {2434} INFO - iteration 55, current learner xgb_limitdepth
[flaml.automl: 01-21 07:54:13] {2594} INFO -  at 9.8s,  estimator xgb_limitdepth's best error=0.0018,   best estimator prophet's best error=0.0005
[flaml.automl: 01-21 07:54:13] {2434} INFO - iteration 56, current learner xgboost
[flaml.automl: 01-21 07:54:13] {2594} INFO -  at 9.8s,  estimator xgboost's best error=0.0242,  best estimator prophet's best error=0.0005
[flaml.automl: 01-21 07:54:13] {2434} INFO - iteration 57, current learner lgbm
[flaml.automl: 01-21 07:54:14] {2594} INFO -  at 9.9s,  estimator lgbm's best error=0.0017,     best estimator prophet's best error=0.0005
[flaml.automl: 01-21 07:54:14] {2434} INFO - iteration 58, current learner rf
[flaml.automl: 01-21 07:54:14] {2594} INFO -  at 10.0s, estimator rf's best error=0.0146,       best estimator prophet's best error=0.0005
[flaml.automl: 01-21 07:54:14] {2824} INFO - retrain prophet for 0.6s
[flaml.automl: 01-21 07:54:14] {2831} INFO - retrained model: <prophet.forecaster.Prophet object at 0x7fb68ea65d60>
[flaml.automl: 01-21 07:54:14] {2210} INFO - fit succeeded
[flaml.automl: 01-21 07:54:14] {2211} INFO - Time taken to find the best model: 9.339771270751953
[flaml.automl: 01-21 07:54:14] {2222} WARNING - Time taken to find the best model is 93% of the provided time budget and not all estimators' hyperparameter search converged. Consider increasing the time budget.
```

#### Compute and plot predictions

The example plotting code requires matplotlib.

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