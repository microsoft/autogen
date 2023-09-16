from flaml.automl.data import load_openml_dataset
from flaml.default import XGBClassifier
from flaml.automl.ml import sklearn_metric_loss_score

X_train, X_test, y_train, y_test = load_openml_dataset(dataset_id=1169, data_dir="./")
xgb = XGBClassifier()
xgb.fit(X_train, y_train)
y_pred = xgb.predict(X_test)
print(
    "flamlized xgb accuracy =",
    1 - sklearn_metric_loss_score("accuracy", y_pred, y_test),
)
print(xgb)
