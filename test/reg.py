from flaml import AutoML
from sklearn.datasets import fetch_california_housing

# Initialize an AutoML instance
automl = AutoML()
# Specify automl goal and constraint
automl_settings = {
    "time_budget": 1,  # in seconds
    "metric": "r2",
    "task": "regression",
    "log_file_name": "test/california.log",
}
X_train, y_train = fetch_california_housing(return_X_y=True)
# Train with labeled input data
automl.fit(X_train=X_train, y_train=y_train, **automl_settings)
print(automl.model)
print(automl.model.estimator)

print(automl.best_estimator)
print(automl.best_config)
print(automl.best_config_per_estimator)

print(automl.best_config_train_time)
print(automl.best_iteration)
print(automl.best_loss)
print(automl.time_to_find_best_model)
print(automl.config_history)
