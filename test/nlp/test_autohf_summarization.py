import sys
import pytest
import requests
from utils import get_toy_data_summarization, get_automl_settings


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_summarization():
    from flaml import AutoML

    X_train, y_train, X_val, y_val, X_test = get_toy_data_summarization()

    automl = AutoML()
    automl_settings = get_automl_settings()

    automl_settings["task"] = "summarization"
    automl_settings["metric"] = "rouge1"
    automl_settings["time_budget"] = 2 * automl_settings["time_budget"]
    automl_settings["fit_kwargs_by_estimator"]["transformer"][
        "model_path"
    ] = "patrickvonplaten/t5-tiny-random"

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

    automl_settings.pop("max_iter", None)
    automl_settings.pop("use_ray", None)
    automl_settings.pop("estimator_list", None)

    automl.retrain_from_log(
        X_train=X_train,
        y_train=y_train,
        train_full=True,
        record_id=0,
        **automl_settings
    )
    automl.predict(X_test)


if __name__ == "__main__":
    test_summarization()
