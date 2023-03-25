import lightgbm as lgb
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from flaml import tune
from flaml.automl.model import LGBMEstimator
from flaml.tune.spark.utils import check_spark
import os
import pytest

spark_available, _ = check_spark()
skip_spark = not spark_available

pytestmark = pytest.mark.skipif(
    skip_spark, reason="Spark is not installed. Skip all spark tests."
)

os.environ["FLAML_MAX_CONCURRENT"] = "2"
X, y = load_breast_cancer(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25)


def train_breast_cancer(config):
    params = LGBMEstimator(**config).params
    train_set = lgb.Dataset(X_train, label=y_train)
    gbm = lgb.train(params, train_set)
    preds = gbm.predict(X_test)
    pred_labels = np.rint(preds)
    result = {
        "mean_accuracy": accuracy_score(y_test, pred_labels),
    }
    return result


def test_tune_spark():
    flaml_lgbm_search_space = LGBMEstimator.search_space(X_train.shape)
    config_search_space = {
        hp: space["domain"] for hp, space in flaml_lgbm_search_space.items()
    }

    analysis = tune.run(
        train_breast_cancer,
        metric="mean_accuracy",
        mode="max",
        config=config_search_space,
        num_samples=-1,
        time_budget_s=5,
        use_spark=True,
        verbose=3,
        n_concurrent_trials=4,
    )

    # print("Best hyperparameters found were: ", analysis.best_config)
    print("The best trial's result: ", analysis.best_trial.last_result)


if __name__ == "__main__":
    test_tune_spark()
