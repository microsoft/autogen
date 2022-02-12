from ray_on_aml.core import Ray_On_AML
from flaml import AutoML


def _test_ray_classification():
    from sklearn.datasets import make_classification

    X, y = make_classification(1000, 10)
    automl = AutoML()
    automl.fit(X, y, time_budget=10, task="classification", n_concurrent_trials=2)


if __name__ == "__main__":
    ray_on_aml = Ray_On_AML()
    ray = ray_on_aml.getRay()
    if ray:
        _test_ray_classification()
