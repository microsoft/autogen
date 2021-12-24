import ray
import lightgbm as lgb
import numpy as np
import sklearn.datasets
import sklearn.metrics
from sklearn.model_selection import train_test_split
from flaml import tune
from flaml.model import LGBMEstimator

data, target = sklearn.datasets.load_breast_cancer(return_X_y=True)
train_x, test_x, train_y, test_y = train_test_split(data, target, test_size=0.25)


def train_breast_cancer(config):
    params = LGBMEstimator(**config).params
    train_set = lgb.Dataset(train_x, label=train_y)
    gbm = lgb.train(params, train_set)
    preds = gbm.predict(test_x)
    pred_labels = np.rint(preds)
    tune.report(
        mean_accuracy=sklearn.metrics.accuracy_score(test_y, pred_labels), done=True
    )


if __name__ == "__main__":
    ray.init(address="auto")
    flaml_lgbm_search_space = LGBMEstimator.search_space(train_x.shape)
    config_search_space = {
        hp: space["domain"] for hp, space in flaml_lgbm_search_space.items()
    }
    low_cost_partial_config = {
        hp: space["low_cost_init_value"]
        for hp, space in flaml_lgbm_search_space.items()
        if "low_cost_init_value" in space
    }

    analysis = tune.run(
        train_breast_cancer,
        metric="mean_accuracy",
        mode="max",
        config=config_search_space,
        num_samples=-1,
        time_budget_s=60,
        use_ray=True,
    )

    # print("Best hyperparameters found were: ", analysis.best_config)
    print("The best trial's result: ", analysis.best_trial.last_result)
