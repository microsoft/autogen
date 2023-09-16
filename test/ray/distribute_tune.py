from ray_on_aml.core import Ray_On_AML
import lightgbm as lgb
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from flaml import tune
from flaml.automl.model import LGBMEstimator


def train_breast_cancer(config):
    params = LGBMEstimator(**config).params
    X_train = ray.get(X_train_ref)
    train_set = lgb.Dataset(X_train, label=y_train)
    gbm = lgb.train(params, train_set)
    preds = gbm.predict(X_test)
    pred_labels = np.rint(preds)
    tune.report(mean_accuracy=accuracy_score(y_test, pred_labels), done=True)


if __name__ == "__main__":
    ray_on_aml = Ray_On_AML()
    ray = ray_on_aml.getRay()
    if ray:
        X, y = load_breast_cancer(return_X_y=True)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25)
        X_train_ref = ray.put(X_train)
        flaml_lgbm_search_space = LGBMEstimator.search_space(X_train.shape)
        config_search_space = {hp: space["domain"] for hp, space in flaml_lgbm_search_space.items()}
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
