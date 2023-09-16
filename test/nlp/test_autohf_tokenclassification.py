import sys
import pytest
import requests
import os
import shutil
from utils import (
    get_toy_data_tokenclassification_idlabel,
    get_toy_data_tokenclassification_tokenlabel,
    get_automl_settings,
)


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or sys.version < "3.7",
    reason="do not run on mac os, windows or py<3.7",
)
def test_tokenclassification_idlabel():
    from flaml import AutoML

    X_train, y_train, X_val, y_val = get_toy_data_tokenclassification_idlabel()
    automl = AutoML()

    automl_settings = get_automl_settings()
    automl_settings["task"] = "token-classification"
    automl_settings["metric"] = "seqeval:overall_f1"  # evaluating based on the overall_f1 of seqeval
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
        automl.fit(X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings)
    except requests.exceptions.HTTPError:
        return

    # perf test
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

    if os.path.exists("test/data/output/"):
        try:
            shutil.rmtree("test/data/output/")
        except PermissionError:
            print("PermissionError when deleting test/data/output/")


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or sys.version < "3.7",
    reason="do not run on mac os, windows or py<3.7",
)
def test_tokenclassification_tokenlabel():
    from flaml import AutoML

    X_train, y_train, X_val, y_val = get_toy_data_tokenclassification_tokenlabel()
    automl = AutoML()

    automl_settings = get_automl_settings()
    automl_settings["task"] = "token-classification"
    automl_settings["metric"] = "seqeval:overall_f1"  # evaluating based on the overall_f1 of seqeval

    try:
        automl.fit(X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings)
    except requests.exceptions.HTTPError:
        return

    # perf test
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

    if os.path.exists("test/data/output/"):
        try:
            shutil.rmtree("test/data/output/")
        except PermissionError:
            print("PermissionError when deleting test/data/output/")


if __name__ == "__main__":
    test_tokenclassification_idlabel()
