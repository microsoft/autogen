from utils import (
    get_toy_data_regression,
    get_toy_data_binclassification,
    get_toy_data_multiclassclassification,
    get_automl_settings,
)
import sys
import pytest
import os
import shutil

data_list = [
    "get_toy_data_regression",
    "get_toy_data_binclassification",
    "get_toy_data_multiclassclassification",
]
model_path_list = [
    "textattack/bert-base-uncased-STS-B",
    "textattack/bert-base-uncased-SST-2",
    "textattack/bert-base-uncased-MNLI",
]


def test_switch_1_1():
    data_idx, model_path_idx = 0, 0
    _test_switch_classificationhead(data_list[data_idx], model_path_list[model_path_idx])


def test_switch_1_2():
    data_idx, model_path_idx = 0, 1
    _test_switch_classificationhead(data_list[data_idx], model_path_list[model_path_idx])


def test_switch_1_3():
    data_idx, model_path_idx = 0, 2
    _test_switch_classificationhead(data_list[data_idx], model_path_list[model_path_idx])


def test_switch_2_1():
    data_idx, model_path_idx = 1, 0
    _test_switch_classificationhead(data_list[data_idx], model_path_list[model_path_idx])


def test_switch_2_2():
    data_idx, model_path_idx = 1, 1
    _test_switch_classificationhead(data_list[data_idx], model_path_list[model_path_idx])


def test_switch_2_3():
    data_idx, model_path_idx = 1, 2
    _test_switch_classificationhead(data_list[data_idx], model_path_list[model_path_idx])


def test_switch_3_1():
    data_idx, model_path_idx = 2, 0
    _test_switch_classificationhead(data_list[data_idx], model_path_list[model_path_idx])


def test_switch_3_2():
    data_idx, model_path_idx = 2, 1
    _test_switch_classificationhead(data_list[data_idx], model_path_list[model_path_idx])


def test_switch_3_3():
    data_idx, model_path_idx = 2, 2
    _test_switch_classificationhead(data_list[data_idx], model_path_list[model_path_idx])


def _test_switch_classificationhead(each_data, each_model_path):
    from flaml import AutoML
    import requests

    automl = AutoML()

    X_train, y_train, X_val, y_val = globals()[each_data]()
    automl_settings = get_automl_settings()
    automl_settings["model_path"] = each_model_path

    if each_data == "get_toy_data_regression":
        automl_settings["task"] = "seq-regression"
        automl_settings["metric"] = "pearsonr"
    else:
        automl_settings["task"] = "seq-classification"
        automl_settings["metric"] = "accuracy"

    try:
        automl.fit(X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings)
    except requests.exceptions.HTTPError:
        return

    if os.path.exists("test/data/output/"):
        try:
            shutil.rmtree("test/data/output/")
        except PermissionError:
            print("PermissionError when deleting test/data/output/")


if __name__ == "__main__":
    _test_switch_classificationhead(data_list[0], model_path_list[0])
