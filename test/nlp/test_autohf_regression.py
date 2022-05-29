import sys
import pytest
from utils import get_toy_data_seqregression, get_automl_settings


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_regression():
    try:
        import ray

        if not ray.is_initialized():
            ray.init()
    except ImportError:
        return
    from flaml import AutoML

    X_train, y_train, X_val, y_val = get_toy_data_seqregression()

    automl = AutoML()
    automl_settings = get_automl_settings()

    automl_settings["task"] = "seq-regression"
    automl_settings["metric"] = "pearsonr"
    automl_settings["starting_points"] = {"transformer": {"num_train_epochs": 1}}
    automl_settings["use_ray"] = {"local_dir": "data/outut/"}

    ray.shutdown()
    ray.init()

    automl.fit(
        X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings
    )
    automl.predict(X_val)


if __name__ == "__main__":
    test_regression()
