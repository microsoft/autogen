import sys
import pytest
import requests
from utils import get_toy_data_seqclassification, get_automl_settings
import os
import shutil


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_hf_data():
    from flaml import AutoML

    X_train, y_train, X_val, y_val, X_test = get_toy_data_seqclassification()

    automl = AutoML()

    automl_settings = get_automl_settings()
    automl_settings["preserve_checkpoint"] = False

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

    import json

    with open("seqclass.log", "r") as fin:
        for line in fin:
            each_log = json.loads(line.strip("\n"))
            if "validation_loss" in each_log:
                val_loss = each_log["validation_loss"]
                min_inter_result = min(
                    each_dict.get("eval_automl_metric", sys.maxsize)
                    for each_dict in each_log["logged_metric"]["intermediate_results"]
                )

                if min_inter_result != sys.maxsize:
                    assert val_loss == min_inter_result

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
    automl.predict(X_test, **{"per_device_eval_batch_size": 2})
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

    del automl

    if os.path.exists("test/data/output/"):
        shutil.rmtree("test/data/output/")


if __name__ == "__main__":
    test_hf_data()
