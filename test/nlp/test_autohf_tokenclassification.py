import sys
import pytest
import requests
from utils import get_toy_data_tokenclassification, get_automl_settings


@pytest.mark.skipif(
    sys.platform == "darwin" or sys.version < "3.7",
    reason="do not run on mac os or py<3.7",
)
def test_tokenclassification():
    from flaml import AutoML

    X_train, y_train, X_val, y_val = get_toy_data_tokenclassification()
    automl = AutoML()

    automl_settings = get_automl_settings()
    automl_settings["task"] = "token-classification"
    automl_settings[
        "metric"
    ] = "seqeval:overall_f1"  # evaluating based on the overall_f1 of seqeval
    automl_settings["fit_kwargs_by_estimator"]["transformer"]["label_list"] = [
        "O",
        "B-PER",
        "I-PER",
        "B-ORG",
        "I-ORG",
        "B-LOC",
        "I-LOC",
        "B-MISC",
        "I-MISC",
    ]

    try:
        automl.fit(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            **automl_settings
        )
    except requests.exceptions.HTTPError:
        return


if __name__ == "__main__":
    test_tokenclassification()
