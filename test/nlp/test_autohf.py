import sys
import pytest
import requests
from utils import get_toy_data_seqclassification, get_automl_settings


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_hf_data():
    from flaml import AutoML

    X_train, y_train, X_val, y_val, X_test = get_toy_data_seqclassification()

    automl = AutoML()

    automl_settings = get_automl_settings()

    try:
        automl.fit(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            **automl_settings
        )
        automl.score(X_val, y_val, **{"metric": "accuracy"})
        automl.pickle("automl.pkl")
    except requests.exceptions.HTTPError:
        return

    automl = AutoML()

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
    automl.predict(["test test", "test test"])
    automl.predict(
        [
            ["test test", "test test"],
            ["test test", "test test"],
            ["test test", "test test"],
        ]
    )

    automl.predict_proba(X_test)
    print(automl.classes_)


if __name__ == "__main__":
    test_hf_data()
