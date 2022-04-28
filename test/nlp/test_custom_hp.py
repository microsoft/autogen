import sys
import pytest
from utils import get_toy_data_seqclassification, get_automl_settings


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_custom_hp_nlp():
    from flaml import AutoML
    import flaml

    X_train, y_train, X_val, y_val, X_test = get_toy_data_seqclassification()

    automl = AutoML()

    automl_settings = get_automl_settings()
    automl_settings["custom_hp"] = None
    automl_settings["custom_hp"] = {
        "transformer": {
            "model_path": {
                "domain": flaml.tune.choice(["google/electra-small-discriminator"]),
            },
            "num_train_epochs": {"domain": 3},
        }
    }
    automl_settings["fit_kwargs_by_estimator"] = {
        "transformer": {
            "output_dir": "test/data/output/",
            "ckpt_per_epoch": 1,
            "fp16": False,
        }
    }
    automl.fit(X_train=X_train, y_train=y_train, **automl_settings)


if __name__ == "__main__":
    test_custom_hp_nlp()
