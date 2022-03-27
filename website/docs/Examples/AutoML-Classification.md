# AutoML - Classification

### A basic classification example

```python
from flaml import AutoML
from sklearn.datasets import load_iris

# Initialize an AutoML instance
automl = AutoML()
# Specify automl goal and constraint
automl_settings = {
    "time_budget": 1,  # in seconds
    "metric": 'accuracy',
    "task": 'classification',
    "log_file_name": "iris.log",
}
X_train, y_train = load_iris(return_X_y=True)
# Train with labeled input data
automl.fit(X_train=X_train, y_train=y_train,
           **automl_settings)
# Predict
print(automl.predict_proba(X_train))
# Print the best model
print(automl.model.estimator)
```

#### Sample of output
```
[flaml.automl: 11-12 18:21:44] {1485} INFO - Data split method: stratified
[flaml.automl: 11-12 18:21:44] {1489} INFO - Evaluation method: cv
[flaml.automl: 11-12 18:21:44] {1540} INFO - Minimizing error metric: 1-accuracy
[flaml.automl: 11-12 18:21:44] {1577} INFO - List of ML learners in AutoML Run: ['lgbm', 'rf', 'catboost', 'xgboost', 'extra_tree', 'lrl1']
[flaml.automl: 11-12 18:21:44] {1826} INFO - iteration 0, current learner lgbm
[flaml.automl: 11-12 18:21:44] {1944} INFO - Estimated sufficient time budget=1285s. Estimated necessary time budget=23s.
[flaml.automl: 11-12 18:21:44] {2029} INFO -  at 0.2s,	estimator lgbm's best error=0.0733,	best estimator lgbm's best error=0.0733
[flaml.automl: 11-12 18:21:44] {1826} INFO - iteration 1, current learner lgbm
[flaml.automl: 11-12 18:21:44] {2029} INFO -  at 0.3s,	estimator lgbm's best error=0.0733,	best estimator lgbm's best error=0.0733
[flaml.automl: 11-12 18:21:44] {1826} INFO - iteration 2, current learner lgbm
[flaml.automl: 11-12 18:21:44] {2029} INFO -  at 0.4s,	estimator lgbm's best error=0.0533,	best estimator lgbm's best error=0.0533
[flaml.automl: 11-12 18:21:44] {1826} INFO - iteration 3, current learner lgbm
[flaml.automl: 11-12 18:21:44] {2029} INFO -  at 0.6s,	estimator lgbm's best error=0.0533,	best estimator lgbm's best error=0.0533
[flaml.automl: 11-12 18:21:44] {1826} INFO - iteration 4, current learner lgbm
[flaml.automl: 11-12 18:21:44] {2029} INFO -  at 0.6s,	estimator lgbm's best error=0.0533,	best estimator lgbm's best error=0.0533
[flaml.automl: 11-12 18:21:44] {1826} INFO - iteration 5, current learner xgboost
[flaml.automl: 11-12 18:21:45] {2029} INFO -  at 0.9s,	estimator xgboost's best error=0.0600,	best estimator lgbm's best error=0.0533
[flaml.automl: 11-12 18:21:45] {1826} INFO - iteration 6, current learner lgbm
[flaml.automl: 11-12 18:21:45] {2029} INFO -  at 1.0s,	estimator lgbm's best error=0.0533,	best estimator lgbm's best error=0.0533
[flaml.automl: 11-12 18:21:45] {1826} INFO - iteration 7, current learner extra_tree
[flaml.automl: 11-12 18:21:45] {2029} INFO -  at 1.1s,	estimator extra_tree's best error=0.0667,	best estimator lgbm's best error=0.0533
[flaml.automl: 11-12 18:21:45] {2242} INFO - retrain lgbm for 0.0s
[flaml.automl: 11-12 18:21:45] {2247} INFO - retrained model: LGBMClassifier(learning_rate=0.2677050123105203, max_bin=127,
               min_child_samples=12, n_estimators=4, num_leaves=4,
               reg_alpha=0.001348364934537134, reg_lambda=1.4442580148221913,
               verbose=-1)
[flaml.automl: 11-12 18:21:45] {1608} INFO - fit succeeded
[flaml.automl: 11-12 18:21:45] {1610} INFO - Time taken to find the best model: 0.3756711483001709
```

### A more advanced example including custom learner and metric

[Link to notebook](https://github.com/microsoft/FLAML/blob/main/notebook/automl_classification.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/FLAML/blob/main/notebook/automl_classification.ipynb)