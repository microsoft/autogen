from flaml.automl.data import load_openml_dataset
from flaml.default import LGBMRegressor
from flaml.automl.ml import sklearn_metric_loss_score

X_train, X_test, y_train, y_test = load_openml_dataset(dataset_id=537, data_dir="./")
lgbm = LGBMRegressor()

hyperparams, estimator_name, X_transformed, y_transformed = lgbm.suggest_hyperparams(X_train, y_train)
print(hyperparams)

lgbm.fit(X_train, y_train)
y_pred = lgbm.predict(X_test)
print("flamlized lgbm r2 =", 1 - sklearn_metric_loss_score("r2", y_pred, y_test))
print(lgbm)
