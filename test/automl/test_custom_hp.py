import sys
import pytest
from flaml import AutoML, tune


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_custom_hp_nlp():
    from test.nlp.utils import get_toy_data_seqclassification, get_automl_settings

    X_train, y_train, X_val, y_val, X_test = get_toy_data_seqclassification()

    automl = AutoML()

    automl_settings = get_automl_settings()
    automl_settings["custom_hp"] = None
    automl_settings["custom_hp"] = {
        "transformer": {
            "model_path": {
                "domain": tune.choice(["google/electra-small-discriminator"]),
            },
            "num_train_epochs": {"domain": 3},
        }
    }
    automl_settings["fit_kwargs_by_estimator"] = {
        "transformer": {
            "output_dir": "test/data/output/",
            "fp16": False,
        }
    }
    automl.fit(X_train=X_train, y_train=y_train, **automl_settings)


def test_custom_hp():
    from sklearn.datasets import load_iris

    X_train, y_train = load_iris(return_X_y=True)
    automl = AutoML()
    custom_hp = {
        "xgboost": {
            "n_estimators": {
                "domain": tune.lograndint(lower=1, upper=100),
                "low_cost_init_value": 1,
            },
        },
        "rf": {
            "max_leaves": {
                "domain": None,  # disable search
            },
        },
        "lgbm": {
            "subsample": {
                "domain": tune.uniform(lower=0.1, upper=1.0),
                "init_value": 1.0,
            },
            "subsample_freq": {
                "domain": 1,  # subsample_freq must > 0 to enable subsample
            },
        },
    }
    automl.fit(X_train, y_train, custom_hp=custom_hp, time_budget=2)
    print(automl.best_config_per_estimator)


if __name__ == "__main__":
    test_custom_hp()
