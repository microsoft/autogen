from utils import get_toy_data_multiclassclassification, get_automl_settings


def test_classification_head():
    from flaml import AutoML
    import requests

    X_train, y_train, X_val, y_val = get_toy_data_multiclassclassification()
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
    except requests.exceptions.HTTPError:
        return


if __name__ == "__main__":
    test_classification_head()
