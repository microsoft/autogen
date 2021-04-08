import unittest

from sklearn.datasets import fetch_openml
from flaml.automl import AutoML
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


dataset = "Airlines"


def _test(split_type):
    automl = AutoML()

    automl_settings = {
        "time_budget": 2,
        # "metric": 'accuracy',
        "task": 'classification',
        "log_file_name": "test/{}.log".format(dataset),
        "model_history": True,
        "log_training_metric": True,
        "split_type": split_type,
    }

    X, y = fetch_openml(name=dataset, return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33,
                                                        random_state=42)
    automl.fit(X_train=X_train, y_train=y_train, **automl_settings)

    pred = automl.predict(X_test)
    acc = accuracy_score(y_test, pred)

    print(acc)


def _test_uniform():
    _test(split_type="uniform")


if __name__ == "__main__":
    unittest.main()
