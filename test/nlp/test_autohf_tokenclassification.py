import sys
import pytest
import requests
from utils import get_toy_data_tokenclassification, get_automl_settings


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_tokenclassification():
    from flaml import AutoML

    X_train, y_train, X_val, y_val = get_toy_data_tokenclassification()
    automl = AutoML()

    automl_settings = get_automl_settings()
    automl_settings["task"] = "token-classification"
    automl_settings["metric"] = "seqeval"

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
