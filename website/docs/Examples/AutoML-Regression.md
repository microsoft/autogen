# AutoML - Regression

### Prerequisites

Install the [automl] option.
```bash
pip install "flaml[automl]"
```

### A basic regression example

```python
from flaml import AutoML
from sklearn.datasets import fetch_california_housing

# Initialize an AutoML instance
automl = AutoML()
# Specify automl goal and constraint
automl_settings = {
    "time_budget": 1,  # in seconds
    "metric": 'r2',
    "task": 'regression',
    "log_file_name": "california.log",
}
X_train, y_train = fetch_california_housing(return_X_y=True)
# Train with labeled input data
automl.fit(X_train=X_train, y_train=y_train,
           **automl_settings)
# Predict
print(automl.predict(X_train))
# Print the best model
print(automl.model.estimator)
```

#### Sample output

```
[flaml.automl: 11-15 07:08:19] {1485} INFO - Data split method: uniform
[flaml.automl: 11-15 07:08:19] {1489} INFO - Evaluation method: holdout
[flaml.automl: 11-15 07:08:19] {1540} INFO - Minimizing error metric: 1-r2
[flaml.automl: 11-15 07:08:19] {1577} INFO - List of ML learners in AutoML Run: ['lgbm', 'rf', 'catboost', 'xgboost', 'extra_tree']
[flaml.automl: 11-15 07:08:19] {1826} INFO - iteration 0, current learner lgbm
[flaml.automl: 11-15 07:08:19] {1944} INFO - Estimated sufficient time budget=846s. Estimated necessary time budget=2s.
[flaml.automl: 11-15 07:08:19] {2029} INFO -  at 0.2s,  estimator lgbm's best error=0.7393,     best estimator lgbm's best error=0.7393
[flaml.automl: 11-15 07:08:19] {1826} INFO - iteration 1, current learner lgbm
[flaml.automl: 11-15 07:08:19] {2029} INFO -  at 0.3s,  estimator lgbm's best error=0.7393,     best estimator lgbm's best error=0.7393
[flaml.automl: 11-15 07:08:19] {1826} INFO - iteration 2, current learner lgbm
[flaml.automl: 11-15 07:08:19] {2029} INFO -  at 0.3s,  estimator lgbm's best error=0.5446,     best estimator lgbm's best error=0.5446
[flaml.automl: 11-15 07:08:19] {1826} INFO - iteration 3, current learner lgbm
[flaml.automl: 11-15 07:08:19] {2029} INFO -  at 0.4s,  estimator lgbm's best error=0.2807,     best estimator lgbm's best error=0.2807
[flaml.automl: 11-15 07:08:19] {1826} INFO - iteration 4, current learner lgbm
[flaml.automl: 11-15 07:08:19] {2029} INFO -  at 0.5s,  estimator lgbm's best error=0.2712,     best estimator lgbm's best error=0.2712
[flaml.automl: 11-15 07:08:19] {1826} INFO - iteration 5, current learner lgbm
[flaml.automl: 11-15 07:08:19] {2029} INFO -  at 0.5s,  estimator lgbm's best error=0.2712,     best estimator lgbm's best error=0.2712
[flaml.automl: 11-15 07:08:19] {1826} INFO - iteration 6, current learner lgbm
[flaml.automl: 11-15 07:08:20] {2029} INFO -  at 0.6s,  estimator lgbm's best error=0.2712,     best estimator lgbm's best error=0.2712
[flaml.automl: 11-15 07:08:20] {1826} INFO - iteration 7, current learner lgbm
[flaml.automl: 11-15 07:08:20] {2029} INFO -  at 0.7s,  estimator lgbm's best error=0.2197,     best estimator lgbm's best error=0.2197
[flaml.automl: 11-15 07:08:20] {1826} INFO - iteration 8, current learner xgboost
[flaml.automl: 11-15 07:08:20] {2029} INFO -  at 0.8s,  estimator xgboost's best error=1.4958,  best estimator lgbm's best error=0.2197
[flaml.automl: 11-15 07:08:20] {1826} INFO - iteration 9, current learner xgboost
[flaml.automl: 11-15 07:08:20] {2029} INFO -  at 0.8s,  estimator xgboost's best error=1.4958,  best estimator lgbm's best error=0.2197
[flaml.automl: 11-15 07:08:20] {1826} INFO - iteration 10, current learner xgboost
[flaml.automl: 11-15 07:08:20] {2029} INFO -  at 0.9s,  estimator xgboost's best error=0.7052,  best estimator lgbm's best error=0.2197
[flaml.automl: 11-15 07:08:20] {1826} INFO - iteration 11, current learner xgboost
[flaml.automl: 11-15 07:08:20] {2029} INFO -  at 0.9s,  estimator xgboost's best error=0.3619,  best estimator lgbm's best error=0.2197
[flaml.automl: 11-15 07:08:20] {1826} INFO - iteration 12, current learner xgboost
[flaml.automl: 11-15 07:08:20] {2029} INFO -  at 0.9s,  estimator xgboost's best error=0.3619,  best estimator lgbm's best error=0.2197
[flaml.automl: 11-15 07:08:20] {1826} INFO - iteration 13, current learner xgboost
[flaml.automl: 11-15 07:08:20] {2029} INFO -  at 1.0s,  estimator xgboost's best error=0.3619,  best estimator lgbm's best error=0.2197
[flaml.automl: 11-15 07:08:20] {1826} INFO - iteration 14, current learner extra_tree
[flaml.automl: 11-15 07:08:20] {2029} INFO -  at 1.1s,  estimator extra_tree's best error=0.7197,       best estimator lgbm's best error=0.2197
[flaml.automl: 11-15 07:08:20] {2242} INFO - retrain lgbm for 0.0s
[flaml.automl: 11-15 07:08:20] {2247} INFO - retrained model: LGBMRegressor(colsample_bytree=0.7610534336273627,
              learning_rate=0.41929025492645006, max_bin=255,
              min_child_samples=4, n_estimators=45, num_leaves=4,
              reg_alpha=0.0009765625, reg_lambda=0.009280655005879943,
              verbose=-1)
[flaml.automl: 11-15 07:08:20] {1608} INFO - fit succeeded
[flaml.automl: 11-15 07:08:20] {1610} INFO - Time taken to find the best model: 0.7289648056030273
[flaml.automl: 11-15 07:08:20] {1624} WARNING - Time taken to find the best model is 73% of the provided time budget and not all estimators' hyperparameter search converged. Consider increasing the time budget.
```

### Multi-output regression

We can combine `sklearn.MultiOutputRegressor` and `flaml.AutoML` to do AutoML for multi-output regression.

```python
from flaml import AutoML
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor

# create regression data
X, y = make_regression(n_targets=3)

# split into train and test data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.30, random_state=42)

# train the model
model = MultiOutputRegressor(AutoML(task="regression", time_budget=60))
model.fit(X_train, y_train)

# predict
print(model.predict(X_test))
```

It will perform AutoML for each target, each taking 60 seconds.
