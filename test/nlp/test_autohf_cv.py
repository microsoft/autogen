import sys
import pytest
from utils import get_toy_data_seqclassification, get_automl_settings
import os
import shutil


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"], reason="do not run on mac os or windows"
)
def test_cv():
    from flaml import AutoML
    import requests

    X_train, y_train, X_val, y_val, X_test = get_toy_data_seqclassification()
    automl = AutoML()

    automl_settings = get_automl_settings()
    automl_settings["n_splits"] = 3

    try:
        automl.fit(X_train=X_train, y_train=y_train, **automl_settings)
    except requests.exceptions.HTTPError:
        return

    if os.path.exists("test/data/output/"):
        try:
            shutil.rmtree("test/data/output/")
        except PermissionError:
            print("PermissionError when deleting test/data/output/")


if __name__ == "__main__":
    test_cv()
