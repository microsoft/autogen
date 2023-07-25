from sklearn.datasets import fetch_openml
from flaml.automl import AutoML
from sklearn.model_selection import GroupKFold, train_test_split, KFold
from sklearn.metrics import accuracy_score


dataset = "credit-g"


def _test(split_type):
    from sklearn.externals._arff import ArffException

    automl = AutoML()

    automl_settings = {
        "time_budget": 2,
        # "metric": 'accuracy',
        "task": "classification",
        "log_file_name": "test/{}.log".format(dataset),
        "model_history": True,
        "log_training_metric": True,
        "split_type": split_type,
    }

    try:
        X, y = fetch_openml(name=dataset, return_X_y=True)
    except (ArffException, ValueError):
        from sklearn.datasets import load_wine

        X, y = load_wine(return_X_y=True)
    if split_type != "time":
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=42)
    else:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, shuffle=False)
    automl.fit(X_train=X_train, y_train=y_train, **automl_settings)

    pred = automl.predict(X_test)
    acc = accuracy_score(y_test, pred)

    print(acc)


def _test_uniform():
    _test(split_type="uniform")


def test_time():
    _test(split_type="time")


def test_groups():
    from sklearn.externals._arff import ArffException

    try:
        X, y = fetch_openml(name=dataset, return_X_y=True)
    except (ArffException, ValueError):
        from sklearn.datasets import load_wine

        X, y = load_wine(return_X_y=True)

    import numpy as np

    automl = AutoML()
    automl_settings = {
        "time_budget": 2,
        "task": "classification",
        "log_file_name": "test/{}.log".format(dataset),
        "model_history": True,
        "eval_method": "cv",
        "groups": np.random.randint(low=0, high=10, size=len(y)),
        "estimator_list": ["lgbm", "rf", "xgboost", "kneighbor"],
        "learner_selector": "roundrobin",
    }
    automl.fit(X, y, **automl_settings)

    automl_settings["eval_method"] = "holdout"
    automl.fit(X, y, **automl_settings)

    automl_settings["split_type"] = GroupKFold(n_splits=3)
    try:
        automl.fit(X, y, **automl_settings)
        raise RuntimeError("GroupKFold object as split_type should fail when eval_method is holdout")
    except AssertionError:
        # eval_method must be 'auto' or 'cv' for custom data splitter.
        pass

    automl_settings["eval_method"] = "cv"
    automl.fit(X, y, **automl_settings)


def test_stratified_groupkfold():
    from sklearn.model_selection import StratifiedGroupKFold
    from minio.error import ServerError
    from flaml.data import load_openml_dataset

    try:
        X_train, _, y_train, _ = load_openml_dataset(dataset_id=1169, data_dir="test/")
    except (ServerError, Exception):
        return
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=0)

    automl = AutoML()
    settings = {
        "time_budget": 6,
        "metric": "ap",
        "eval_method": "cv",
        "split_type": splitter,
        "groups": X_train["Airline"],
        "estimator_list": [
            "lgbm",
            "rf",
            "xgboost",
            "extra_tree",
            "xgb_limitdepth",
            "lrl1",
        ],
    }

    automl.fit(X_train=X_train, y_train=y_train, **settings)


def test_rank():
    from sklearn.externals._arff import ArffException

    try:
        X, y = fetch_openml(name=dataset, return_X_y=True)
        y = y.cat.codes
    except (ArffException, ValueError):
        from sklearn.datasets import load_wine

        X, y = load_wine(return_X_y=True)
    import numpy as np

    automl = AutoML()
    automl_settings = {
        "time_budget": 2,
        "task": "rank",
        "log_file_name": "test/{}.log".format(dataset),
        "model_history": True,
        "eval_method": "cv",
        "groups": np.array([0] * 200 + [1] * 200 + [2] * 200 + [3] * 200 + [4] * 100 + [5] * 100),  # group labels
        "learner_selector": "roundrobin",
    }
    automl.fit(X, y, **automl_settings)

    automl = AutoML()
    automl_settings = {
        "time_budget": 2,
        "task": "rank",
        "metric": "ndcg@5",  # 5 can be replaced by any number
        "log_file_name": "test/{}.log".format(dataset),
        "model_history": True,
        "groups": [200] * 4 + [100] * 2,  # alternative way: group counts
        # "estimator_list": ['lgbm', 'xgboost'],  # list of ML learners
        "learner_selector": "roundrobin",
    }
    automl.fit(X, y, **automl_settings)


def test_object():
    from sklearn.externals._arff import ArffException

    try:
        X, y = fetch_openml(name=dataset, return_X_y=True)
    except (ArffException, ValueError):
        from sklearn.datasets import load_wine

        X, y = load_wine(return_X_y=True)

    import numpy as np

    class TestKFold(KFold):
        def __init__(self, n_splits):
            self.n_splits = int(n_splits)

        def split(self, X):
            rng = np.random.default_rng()
            train_num = int(len(X) * 0.8)
            for _ in range(self.n_splits):
                permu_idx = rng.permutation(len(X))
                yield permu_idx[:train_num], permu_idx[train_num:]

        def get_n_splits(self, X=None, y=None, groups=None):
            return self.n_splits

    automl = AutoML()
    automl_settings = {
        "time_budget": 2,
        "task": "classification",
        "log_file_name": "test/{}.log".format(dataset),
        "model_history": True,
        "log_training_metric": True,
        "split_type": TestKFold(5),
    }
    automl.fit(X, y, **automl_settings)
    assert automl._state.eval_method == "cv", "eval_method must be 'cv' for custom data splitter"

    kf = TestKFold(5)
    kf.shuffle = True
    automl_settings["split_type"] = kf
    automl.fit(X, y, **automl_settings)


if __name__ == "__main__":
    test_groups()
