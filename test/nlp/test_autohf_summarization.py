import sys
import pytest
import requests
from utils import get_toy_data_summarization, get_automl_settings
import os
import shutil


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or sys.version < "3.7",
    reason="do not run on mac os, windows or py3.6",
)
def test_summarization():
    # TODO: manual test for how effective postprocess_seq2seq_prediction_label is
    from flaml import AutoML

    X_train, y_train, X_val, y_val, X_test = get_toy_data_summarization()

    automl = AutoML()
    automl_settings = get_automl_settings()

    automl_settings["task"] = "summarization"
    automl_settings["metric"] = "rouge1"
    automl_settings["time_budget"] = 2 * automl_settings["time_budget"]
    automl_settings["fit_kwargs_by_estimator"]["transformer"]["model_path"] = "google/flan-t5-small"

    try:
        automl.fit(X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings)
    except requests.exceptions.HTTPError:
        return

    automl_settings.pop("max_iter", None)
    automl_settings.pop("use_ray", None)
    automl_settings.pop("estimator_list", None)

    automl.retrain_from_log(X_train=X_train, y_train=y_train, train_full=True, record_id=0, **automl_settings)
    automl.predict(X_test)

    if os.path.exists("test/data/output/"):
        try:
            shutil.rmtree("test/data/output/")
        except PermissionError:
            print("PermissionError when deleting test/data/output/")


if __name__ == "__main__":
    test_summarization()
