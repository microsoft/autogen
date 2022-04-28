from utils import get_toy_data_seqclassification, get_automl_settings
import sys
from flaml.default import portfolio


def pop_args(fit_kwargs):
    fit_kwargs.pop("max_iter", None)
    fit_kwargs.pop("use_ray", None)
    fit_kwargs.pop("estimator_list", None)
    fit_kwargs.pop("time_budget", None)
    fit_kwargs.pop("log_file_name", None)


def test_build_portfolio(path="./test/nlp/default", strategy="greedy"):
    sys.argv = f"portfolio.py --output {path} --input {path} --metafeatures {path}/all/metafeatures.csv --task seq-classification --estimator transformer_ms --strategy {strategy}".split()
    portfolio.main()


def test_starting_point_not_in_search_space():
    from flaml import AutoML

    """
        test starting_points located outside of the search space, and custom_hp is not set
    """
    this_estimator_name = "transformer"
    X_train, y_train, X_val, y_val, _ = get_toy_data_seqclassification()

    automl = AutoML()
    automl_settings = get_automl_settings(estimator_name=this_estimator_name)

    automl_settings["starting_points"] = {
        this_estimator_name: [{"learning_rate": 2e-3}]
    }

    automl.fit(X_train, y_train, **automl_settings)
    assert (
        automl._search_states[this_estimator_name].init_config["learning_rate"] != 2e-3
    )

    """
        test starting_points located outside of the search space, and custom_hp is set
    """

    from flaml import tune

    X_train, y_train, X_val, y_val, _ = get_toy_data_seqclassification()

    this_estimator_name = "transformer_ms"
    automl = AutoML()
    automl_settings = get_automl_settings(estimator_name=this_estimator_name)

    automl_settings["custom_hp"] = {
        this_estimator_name: {
            "model_path": {
                "domain": "albert-base-v2",
            },
            "learning_rate": {
                "domain": tune.choice([1e-4, 1e-5]),
            },
        }
    }
    automl_settings["starting_points"] = "data:test/nlp/default/"
    del automl_settings["fit_kwargs_by_estimator"][this_estimator_name]["model_path"]

    automl.fit(X_train, y_train, **automl_settings)
    assert (
        len(automl._search_states[this_estimator_name].init_config) == 0
    )  # check that init config is not updated, but search space is updated
    assert (
        automl._search_states[this_estimator_name].search_space["model_path"]
        == "albert-base-v2"
    )


def test_points_to_evaluate():
    from flaml import AutoML

    X_train, y_train, X_val, y_val, _ = get_toy_data_seqclassification()

    automl = AutoML()
    automl_settings = get_automl_settings(estimator_name="transformer_ms")

    automl_settings["estimator_list"] = ["transformer_ms"]
    automl_settings["starting_points"] = "data"

    del automl_settings["fit_kwargs_by_estimator"]["transformer_ms"]["model_path"]

    automl.fit(X_train, y_train, **automl_settings)


# TODO: implement _test_zero_shot_model
def test_zero_shot_nomodel():
    from flaml.default import preprocess_and_suggest_hyperparams

    estimator_name = "transformer_ms"

    location = "test/nlp/default"
    X_train, y_train, X_val, y_val, X_test = get_toy_data_seqclassification()

    automl_settings = get_automl_settings(estimator_name)

    del automl_settings["fit_kwargs_by_estimator"][estimator_name]["model_path"]

    (
        hyperparams,
        estimator_class,
        X_train,
        y_train,
        _,
        _,
    ) = preprocess_and_suggest_hyperparams(
        "seq-classification", X_train, y_train, estimator_name, location=location
    )

    model = estimator_class(
        **hyperparams
    )  # estimator_class is TransformersEstimatorModelSelection

    fit_kwargs = automl_settings.pop("fit_kwargs_by_estimator", {}).get(estimator_name)
    fit_kwargs.update(automl_settings)
    pop_args(fit_kwargs)
    model.fit(X_train, y_train, **fit_kwargs)


def test_build_error_portfolio(path="./test/nlp/default", strategy="greedy"):
    import os

    os.remove("./test/nlp/default/transformer_ms/seq-classification.json")
    sys.argv = f"portfolio.py --output {path} --input {path} --metafeatures {path}/all/metafeatures_err.csv --task seq-classification --estimator transformer_ms --strategy {strategy}".split()
    portfolio.main()

    from flaml.default import preprocess_and_suggest_hyperparams

    estimator_name = "transformer_ms"

    location = "test/nlp/default"
    X_train, y_train, X_val, y_val, X_test = get_toy_data_seqclassification()

    automl_settings = get_automl_settings(estimator_name)

    del automl_settings["fit_kwargs_by_estimator"][estimator_name]["model_path"]

    try:
        (
            hyperparams,
            estimator_class,
            X_train,
            y_train,
            _,
            _,
        ) = preprocess_and_suggest_hyperparams(
            "seq-classification", X_train, y_train, estimator_name, location=location
        )
    except ValueError:
        print("Feature not implemented")
