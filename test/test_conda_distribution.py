import pytest
from pathlib import Path
from flaml import AutoML
from sklearn.datasets import load_iris


@pytest.mark.conda
def test_package_minimum():
    # Initialize an AutoML instance
    automl = AutoML()
    # Specify automl goal and constraint
    automl_settings = {
        "time_budget": 10,  # in seconds
        "metric": "accuracy",
        "task": "classification",
        "log_file_name": "iris.log",
    }
    X_train, y_train = load_iris(return_X_y=True)
    # Train with labeled input data
    automl.fit(X_train=X_train, y_train=y_train, **automl_settings)
    # Check that `best_config` is created, the log was created and best model is accessible
    assert hasattr(automl, "best_config")
    assert Path("iris.log").exists()
    assert automl.model is not None
    print(automl.model)
    # Predict and check that the prediction shape is as expected
    preds = automl.predict_proba(X_train)
    assert preds.shape == (150, 3)
    print(preds)
