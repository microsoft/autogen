# AutoML - Rank

### Prerequisites

Install the [automl] option.
```bash
pip install "flaml[automl]"
```

### A simple learning-to-rank example

```python
from sklearn.datasets import fetch_openml
from flaml import AutoML

X_train, y_train = fetch_openml(name="credit-g", return_X_y=True, as_frame=False)
y_train = y_train.cat.codes
# not a real learning to rank dataaset
groups = [200] * 4 + [100] * 2    # group counts
automl = AutoML()
automl.fit(
    X_train, y_train, groups=groups,
    task='rank', time_budget=10,    # in seconds
)
```

#### Sample output

```
[flaml.automl: 11-15 07:14:30] {1485} INFO - Data split method: group
[flaml.automl: 11-15 07:14:30] {1489} INFO - Evaluation method: holdout
[flaml.automl: 11-15 07:14:30] {1540} INFO - Minimizing error metric: 1-ndcg
[flaml.automl: 11-15 07:14:30] {1577} INFO - List of ML learners in AutoML Run: ['lgbm', 'xgboost']
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 0, current learner lgbm
[flaml.automl: 11-15 07:14:30] {1944} INFO - Estimated sufficient time budget=679s. Estimated necessary time budget=1s.
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.1s,  estimator lgbm's best error=0.0248,     best estimator lgbm's best error=0.0248
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 1, current learner lgbm
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.1s,  estimator lgbm's best error=0.0248,     best estimator lgbm's best error=0.0248
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 2, current learner lgbm
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.2s,  estimator lgbm's best error=0.0248,     best estimator lgbm's best error=0.0248
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 3, current learner lgbm
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.2s,  estimator lgbm's best error=0.0248,     best estimator lgbm's best error=0.0248
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 4, current learner xgboost
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.2s,  estimator xgboost's best error=0.0315,  best estimator lgbm's best error=0.0248
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 5, current learner xgboost
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.2s,  estimator xgboost's best error=0.0315,  best estimator lgbm's best error=0.0248
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 6, current learner lgbm
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.3s,  estimator lgbm's best error=0.0248,     best estimator lgbm's best error=0.0248
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 7, current learner lgbm
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.3s,  estimator lgbm's best error=0.0248,     best estimator lgbm's best error=0.0248
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 8, current learner xgboost
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.4s,  estimator xgboost's best error=0.0315,  best estimator lgbm's best error=0.0248
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 9, current learner xgboost
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.4s,  estimator xgboost's best error=0.0315,  best estimator lgbm's best error=0.0248
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 10, current learner xgboost
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.4s,  estimator xgboost's best error=0.0233,  best estimator xgboost's best error=0.0233
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 11, current learner xgboost
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.4s,  estimator xgboost's best error=0.0233,  best estimator xgboost's best error=0.0233
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 12, current learner xgboost
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.4s,  estimator xgboost's best error=0.0233,  best estimator xgboost's best error=0.0233
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 13, current learner xgboost
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.4s,  estimator xgboost's best error=0.0233,  best estimator xgboost's best error=0.0233
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 14, current learner lgbm
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.5s,  estimator lgbm's best error=0.0225,     best estimator lgbm's best error=0.0225
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 15, current learner xgboost
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.5s,  estimator xgboost's best error=0.0233,  best estimator lgbm's best error=0.0225
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 16, current learner lgbm
[flaml.automl: 11-15 07:14:30] {2029} INFO -  at 0.5s,  estimator lgbm's best error=0.0225,     best estimator lgbm's best error=0.0225
[flaml.automl: 11-15 07:14:30] {1826} INFO - iteration 17, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 0.5s,  estimator lgbm's best error=0.0225,     best estimator lgbm's best error=0.0225
[flaml.automl: 11-15 07:14:31] {1826} INFO - iteration 18, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 0.6s,  estimator lgbm's best error=0.0225,     best estimator lgbm's best error=0.0225
[flaml.automl: 11-15 07:14:31] {1826} INFO - iteration 19, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 0.6s,  estimator lgbm's best error=0.0201,     best estimator lgbm's best error=0.0201
[flaml.automl: 11-15 07:14:31] {1826} INFO - iteration 20, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 0.6s,  estimator lgbm's best error=0.0201,     best estimator lgbm's best error=0.0201
[flaml.automl: 11-15 07:14:31] {1826} INFO - iteration 21, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 0.7s,  estimator lgbm's best error=0.0201,     best estimator lgbm's best error=0.0201
[flaml.automl: 11-15 07:14:31] {1826} INFO - iteration 22, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 0.7s,  estimator lgbm's best error=0.0201,     best estimator lgbm's best error=0.0201
[flaml.automl: 11-15 07:14:31] {1826} INFO - iteration 23, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 0.8s,  estimator lgbm's best error=0.0201,     best estimator lgbm's best error=0.0201
[flaml.automl: 11-15 07:14:31] {1826} INFO - iteration 24, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 0.8s,  estimator lgbm's best error=0.0201,     best estimator lgbm's best error=0.0201
[flaml.automl: 11-15 07:14:31] {1826} INFO - iteration 25, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 0.8s,  estimator lgbm's best error=0.0201,     best estimator lgbm's best error=0.0201
[flaml.automl: 11-15 07:14:31] {1826} INFO - iteration 26, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 0.9s,  estimator lgbm's best error=0.0197,     best estimator lgbm's best error=0.0197
[flaml.automl: 11-15 07:14:31] {1826} INFO - iteration 27, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 0.9s,  estimator lgbm's best error=0.0197,     best estimator lgbm's best error=0.0197
[flaml.automl: 11-15 07:14:31] {1826} INFO - iteration 28, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 1.0s,  estimator lgbm's best error=0.0197,     best estimator lgbm's best error=0.0197
[flaml.automl: 11-15 07:14:31] {1826} INFO - iteration 29, current learner lgbm
[flaml.automl: 11-15 07:14:31] {2029} INFO -  at 1.0s,  estimator lgbm's best error=0.0197,     best estimator lgbm's best error=0.0197
[flaml.automl: 11-15 07:14:31] {2242} INFO - retrain lgbm for 0.0s
[flaml.automl: 11-15 07:14:31] {2247} INFO - retrained model: LGBMRanker(colsample_bytree=0.9852774042640857,
           learning_rate=0.034918421933217675, max_bin=1023,
           min_child_samples=22, n_estimators=6, num_leaves=23,
           reg_alpha=0.0009765625, reg_lambda=21.505295697527654, verbose=-1)
[flaml.automl: 11-15 07:14:31] {1608} INFO - fit succeeded
[flaml.automl: 11-15 07:14:31] {1610} INFO - Time taken to find the best model: 0.8846545219421387
[flaml.automl: 11-15 07:14:31] {1624} WARNING - Time taken to find the best model is 88% of the provided time budget and not all estimators' hyperparameter search converged. Consider increasing the time budget.
```
