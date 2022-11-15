import sys
import pickle
from sklearn.datasets import load_iris, fetch_california_housing, load_breast_cancer
from sklearn.model_selection import train_test_split
import pandas as pd
from flaml import AutoML
from flaml.default import (
    portfolio,
    regret,
    preprocess_and_suggest_hyperparams,
    suggest_hyperparams,
    suggest_learner,
)


def test_greedy_feedback(path="test/default", strategy="greedy-feedback"):
    # sys.argv = f"portfolio.py --output {path} --input {path} --metafeatures {path}/all/metafeatures.csv --task binary --estimator lgbm xgboost xgb_limitdepth rf extra_tree --strategy {strategy}".split()
    # portfolio.main()
    # sys.argv = f"portfolio.py --output {path} --input {path} --metafeatures {path}/all/metafeatures.csv --task multiclass --estimator lgbm xgboost xgb_limitdepth rf extra_tree --strategy {strategy}".split()
    # portfolio.main()
    sys.argv = f"portfolio.py --output {path} --input {path} --metafeatures {path}/all/metafeatures.csv --task regression --estimator lgbm --strategy {strategy}".split()
    portfolio.main()


def test_build_portfolio(path="test/default", strategy="greedy"):
    sys.argv = f"portfolio.py --output {path} --input {path} --metafeatures {path}/all/metafeatures.csv --task binary --estimator lgbm xgboost xgb_limitdepth rf extra_tree --strategy {strategy}".split()
    portfolio.main()
    sys.argv = f"portfolio.py --output {path} --input {path} --metafeatures {path}/all/metafeatures.csv --task multiclass --estimator lgbm xgboost xgb_limitdepth rf extra_tree --strategy {strategy}".split()
    portfolio.main()
    sys.argv = f"portfolio.py --output {path} --input {path} --metafeatures {path}/all/metafeatures.csv --task regression --estimator lgbm xgboost xgb_limitdepth rf extra_tree --strategy {strategy}".split()
    portfolio.main()


def test_iris(as_frame=True):
    automl = AutoML()
    automl_settings = {
        "time_budget": 2,
        "metric": "accuracy",
        "task": "classification",
        "log_file_name": "test/iris.log",
        "n_jobs": 1,
        "starting_points": "data",
    }
    X_train, y_train = load_iris(return_X_y=True, as_frame=as_frame)
    automl.fit(X_train, y_train, **automl_settings)
    automl_settings["starting_points"] = "data:test/default"
    automl.fit(X_train, y_train, **automl_settings)


def test_housing(as_frame=True):
    automl = AutoML()
    automl_settings = {
        "time_budget": 2,
        "task": "regression",
        "estimator_list": ["xgboost", "lgbm"],
        "log_file_name": "test/housing.log",
        "n_jobs": 1,
        "starting_points": "data",
        "max_iter": 0,
    }
    X_train, y_train = fetch_california_housing(return_X_y=True, as_frame=as_frame)
    automl.fit(X_train, y_train, **automl_settings)


def test_regret():
    sys.argv = "regret.py --result_csv test/default/lgbm/results.csv --task_type binary --output test/default/lgbm/binary_regret.csv".split()
    regret.main()


def test_suggest_classification():
    location = "test/default"
    X_train, y_train = load_breast_cancer(return_X_y=True, as_frame=True)
    suggested = suggest_hyperparams(
        "classification", X_train, y_train, "lgbm", location=location
    )
    print(suggested)
    suggested = preprocess_and_suggest_hyperparams(
        "classification", X_train, y_train, "xgboost", location=location
    )
    print(suggested)
    suggested = suggest_hyperparams(
        "classification", X_train, y_train, "xgb_limitdepth", location=location
    )
    print(suggested)

    X, y = load_iris(return_X_y=True, as_frame=True)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.33, random_state=42
    )
    (
        hyperparams,
        estimator_class,
        X,
        y,
        feature_transformer,
        label_transformer,
    ) = preprocess_and_suggest_hyperparams(
        "classification", X_train, y_train, "lgbm", location=location
    )
    with open("test/default/feature_transformer", "wb") as f:
        pickle.dump(feature_transformer, f, pickle.HIGHEST_PROTOCOL)
    model = estimator_class(**hyperparams)  # estimator_class is LGBMClassifier
    model.fit(X, y)
    X_test = feature_transformer.transform(X_test)
    y_pred = label_transformer.inverse_transform(
        pd.Series(model.predict(X_test).astype(int))
    )
    print(y_pred)
    suggested = suggest_hyperparams(
        "classification", X_train, y_train, "xgboost", location=location
    )
    print(suggested)
    suggested = preprocess_and_suggest_hyperparams(
        "classification", X_train, y_train, "xgb_limitdepth", location=location
    )
    print(suggested)
    suggested = suggest_hyperparams(
        "classification", X_train, y_train, "xgb_limitdepth", location=location
    )
    suggested = suggest_learner(
        "classification",
        X_train,
        y_train,
        estimator_list=["xgboost", "xgb_limitdepth"],
        location=location,
    )
    print(suggested)


def test_suggest_regression():
    location = "test/default"
    X_train, y_train = fetch_california_housing(return_X_y=True, as_frame=True)
    suggested = suggest_hyperparams(
        "regression", X_train, y_train, "lgbm", location=location
    )
    print(suggested)
    suggested = preprocess_and_suggest_hyperparams(
        "regression", X_train, y_train, "xgboost", location=location
    )
    print(suggested)
    suggested = suggest_hyperparams(
        "regression", X_train, y_train, "xgb_limitdepth", location=location
    )
    print(suggested)
    suggested = suggest_learner("regression", X_train, y_train, location=location)
    print(suggested)


def test_rf():
    from flaml.default.estimator import RandomForestRegressor, RandomForestClassifier

    X_train, y_train = load_breast_cancer(return_X_y=True, as_frame=True)
    rf = RandomForestClassifier()
    rf.fit(X_train[:100], y_train[:100])
    rf.predict(X_train)
    rf.predict_proba(X_train)
    print(rf)

    location = "test/default"
    X_train, y_train = fetch_california_housing(return_X_y=True, as_frame=True)
    rf = RandomForestRegressor(default_location=location)
    rf.fit(X_train[:100], y_train[:100])
    rf.predict(X_train)
    print(rf)


def test_extratrees():
    from flaml.default.estimator import ExtraTreesRegressor, ExtraTreesClassifier

    X_train, y_train = load_iris(return_X_y=True, as_frame=True)
    classifier = ExtraTreesClassifier()
    classifier.fit(X_train[:100], y_train[:100])
    classifier.predict(X_train)
    classifier.predict_proba(X_train)
    print(classifier)

    location = "test/default"
    X_train, y_train = fetch_california_housing(return_X_y=True, as_frame=True)
    regressor = ExtraTreesRegressor(default_location=location)
    regressor.fit(X_train[:100], y_train[:100])
    regressor.predict(X_train)
    print(regressor)


def test_lgbm():
    from flaml.default.estimator import LGBMRegressor, LGBMClassifier

    X_train, y_train = load_breast_cancer(return_X_y=True, as_frame=True)
    classifier = LGBMClassifier(n_jobs=1)
    classifier.fit(X_train, y_train)
    classifier.predict(X_train, pred_contrib=True)
    classifier.predict_proba(X_train)
    print(classifier.get_params())
    print(classifier)
    print(classifier.classes_)

    location = "test/default"
    X_train, y_train = fetch_california_housing(return_X_y=True, as_frame=True)
    regressor = LGBMRegressor(default_location=location)
    regressor.fit(X_train, y_train)
    regressor.predict(X_train)
    print(regressor)


def test_xgboost():
    from flaml.default.estimator import XGBRegressor, XGBClassifier

    X_train, y_train = load_breast_cancer(return_X_y=True, as_frame=True)
    classifier = XGBClassifier(max_depth=0)
    classifier.fit(X_train[:100], y_train[:100])
    classifier.predict(X_train)
    classifier.predict_proba(X_train)
    print(classifier)
    print(classifier.classes_)

    location = "test/default"
    X_train, y_train = fetch_california_housing(return_X_y=True, as_frame=True)
    regressor = XGBRegressor(default_location=location)
    regressor.fit(X_train[:100], y_train[:100])
    regressor.predict(X_train)
    print(regressor)


def test_nobudget():
    X_train, y_train = load_breast_cancer(return_X_y=True, as_frame=True)
    automl = AutoML()
    automl.fit(
        X_train[:20],
        y_train[:20],
        estimator_list=["lgbm", "extra_tree", "rf"],
        max_iter=12,
        starting_points="data",
        log_file_name="test/default/no_budget.txt",
        log_type="all",
    )
    automl.fit(X_train[:20], y_train[:20], estimator_list=["lgbm", "extra_tree", "rf"])
    # make sure that zero-shot config out of the search space does not degnerate to low cost init config
    assert automl.best_config_per_estimator["extra_tree"]["n_estimators"] > 4
    # make sure that the zero-shot config {} is not modified
    assert "criterion" not in automl.best_config_per_estimator["rf"]


if __name__ == "__main__":
    test_build_portfolio("flaml/default")
