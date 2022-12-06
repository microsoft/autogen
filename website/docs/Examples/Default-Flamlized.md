# Default - Flamlized Estimator

Flamlized estimators automatically use data-dependent default hyperparameter configurations for each estimator, offering a unique zero-shot AutoML capability, or "no tuning" AutoML.

This example requires openml==0.10.2.

## Flamlized LGBMRegressor

### Zero-shot AutoML

```python
from flaml.automl.data import load_openml_dataset
from flaml.default import LGBMRegressor
from flaml.automl.ml import sklearn_metric_loss_score

X_train, X_test, y_train, y_test = load_openml_dataset(dataset_id=537, data_dir="./")
lgbm = LGBMRegressor()
lgbm.fit(X_train, y_train)
y_pred = lgbm.predict(X_test)
print("flamlized lgbm r2", "=", 1 - sklearn_metric_loss_score("r2", y_pred, y_test))
print(lgbm)
```

#### Sample output

```
load dataset from ./openml_ds537.pkl
Dataset name: houses
X_train.shape: (15480, 8), y_train.shape: (15480,);
X_test.shape: (5160, 8), y_test.shape: (5160,)
flamlized lgbm r2 = 0.8537444671194614
LGBMRegressor(colsample_bytree=0.7019911744574896,
              learning_rate=0.022635758411078528, max_bin=511,
              min_child_samples=2, n_estimators=4797, num_leaves=122,
              reg_alpha=0.004252223402511765, reg_lambda=0.11288241427227624,
              verbose=-1)
```

### Suggest hyperparameters without training

```
from flaml.data import load_openml_dataset
from flaml.default import LGBMRegressor
from flaml.ml import sklearn_metric_loss_score

X_train, X_test, y_train, y_test = load_openml_dataset(dataset_id=537, data_dir="./")
lgbm = LGBMRegressor()
hyperparams, estimator_name, X_transformed, y_transformed = lgbm.suggest_hyperparams(X_train, y_train)
print(hyperparams)
```

#### Sample output
```
load dataset from ./openml_ds537.pkl
Dataset name: houses
X_train.shape: (15480, 8), y_train.shape: (15480,);
X_test.shape: (5160, 8), y_test.shape: (5160,)
{'n_estimators': 4797, 'num_leaves': 122, 'min_child_samples': 2, 'learning_rate': 0.022635758411078528, 'colsample_bytree': 0.7019911744574896, 'reg_alpha': 0.004252223402511765, 'reg_lambda': 0.11288241427227624, 'max_bin': 511, 'verbose': -1}
```

[Link to notebook](https://github.com/microsoft/FLAML/blob/main/notebook/zeroshot_lightgbm.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/FLAML/blob/main/notebook/zeroshot_lightgbm.ipynb)

## Flamlized XGBClassifier

### Zero-shot AutoML

```python
from flaml.automl.data import load_openml_dataset
from flaml.default import XGBClassifier
from flaml.automl.ml import sklearn_metric_loss_score

X_train, X_test, y_train, y_test = load_openml_dataset(dataset_id=1169, data_dir="./")
xgb = XGBClassifier()
xgb.fit(X_train, y_train)
y_pred = xgb.predict(X_test)
print("flamlized xgb accuracy", "=", 1 - sklearn_metric_loss_score("accuracy", y_pred, y_test))
print(xgb)
```

#### Sample output

```
load dataset from ./openml_ds1169.pkl
Dataset name: airlines
X_train.shape: (404537, 7), y_train.shape: (404537,);
X_test.shape: (134846, 7), y_test.shape: (134846,)
flamlized xgb accuracy = 0.6729009388487608
XGBClassifier(base_score=0.5, booster='gbtree',
              colsample_bylevel=0.4601573737792679, colsample_bynode=1,
              colsample_bytree=1.0, gamma=0, gpu_id=-1, grow_policy='lossguide',
              importance_type='gain', interaction_constraints='',
              learning_rate=0.04039771837785377, max_delta_step=0, max_depth=0,
              max_leaves=159, min_child_weight=0.3396294979905001, missing=nan,
              monotone_constraints='()', n_estimators=540, n_jobs=4,
              num_parallel_tree=1, random_state=0,
              reg_alpha=0.0012362430984376035, reg_lambda=3.093428791531145,
              scale_pos_weight=1, subsample=1.0, tree_method='hist',
              use_label_encoder=False, validate_parameters=1, verbosity=0)
```
