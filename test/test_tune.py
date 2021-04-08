'''Require: pip install flaml[test,ray]
'''
import unittest
import time
from sklearn.model_selection import train_test_split
import sklearn.metrics
import sklearn.datasets
try:
    from ray.tune.integration.xgboost import TuneReportCheckpointCallback
except ImportError:
    print("skip test_tune because ray tune cannot be imported.")
import xgboost as xgb

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.FileHandler('test/tune_xgboost.log'))


def train_breast_cancer(config: dict):
    # This is a simple training function to be passed into Tune
    # Load dataset
    data, labels = sklearn.datasets.load_breast_cancer(return_X_y=True)
    # Split into train and test set
    train_x, test_x, train_y, test_y = train_test_split(
        data, labels, test_size=0.25)
    # Build input matrices for XGBoost
    train_set = xgb.DMatrix(train_x, label=train_y)
    test_set = xgb.DMatrix(test_x, label=test_y)
    # HyperOpt returns a tuple
    config = config.copy()
    config["eval_metric"] = ["logloss", "error"]
    config["objective"] = "binary:logistic"
    # Train the classifier, using the Tune callback
    xgb.train(
        config,
        train_set,
        evals=[(test_set, "eval")],
        verbose_eval=False,
        callbacks=[TuneReportCheckpointCallback(filename="model.xgb")])


def _test_xgboost(method='BlendSearch'):
    try:
        import ray
    except ImportError:
        return
    if method == 'BlendSearch':
        from flaml import tune
    else:
        from ray import tune
    search_space = {
        "max_depth": tune.randint(1, 8) if method in [
            "BlendSearch", "BOHB", "Optuna"] else tune.randint(1, 9),
        "min_child_weight": tune.choice([1, 2, 3]),
        "subsample": tune.uniform(0.5, 1.0),
        "eta": tune.loguniform(1e-4, 1e-1)
    }
    max_iter = 10
    for num_samples in [128]:
        time_budget_s = 60
        for n_cpu in [8]:
            start_time = time.time()
            ray.init(num_cpus=n_cpu, num_gpus=0)
            if method == 'BlendSearch':
                analysis = tune.run(
                    train_breast_cancer,
                    config=search_space,
                    low_cost_partial_config={
                        "max_depth": 1,
                    },
                    cat_hp_cost={
                        "min_child_weight": [6, 3, 2],
                    },
                    metric="eval-logloss",
                    mode="min",
                    max_resource=max_iter,
                    min_resource=1,
                    report_intermediate_result=True,
                    # You can add "gpu": 0.1 to allocate GPUs
                    resources_per_trial={"cpu": 1},
                    local_dir='logs/',
                    num_samples=num_samples * n_cpu,
                    time_budget_s=time_budget_s,
                    use_ray=True)
            else:
                if 'ASHA' == method:
                    algo = None
                elif 'BOHB' == method:
                    from ray.tune.schedulers import HyperBandForBOHB
                    from ray.tune.suggest.bohb import TuneBOHB
                    algo = TuneBOHB(max_concurrent=n_cpu)
                    scheduler = HyperBandForBOHB(max_t=max_iter)
                elif 'Optuna' == method:
                    from ray.tune.suggest.optuna import OptunaSearch
                    algo = OptunaSearch()
                elif 'CFO' == method:
                    from flaml import CFO
                    algo = CFO(low_cost_partial_config={
                        "max_depth": 1,
                    }, cat_hp_cost={
                        "min_child_weight": [6, 3, 2],
                    })
                elif 'Dragonfly' == method:
                    from ray.tune.suggest.dragonfly import DragonflySearch
                    algo = DragonflySearch()
                elif 'SkOpt' == method:
                    from ray.tune.suggest.skopt import SkOptSearch
                    algo = SkOptSearch()
                elif 'Nevergrad' == method:
                    from ray.tune.suggest.nevergrad import NevergradSearch
                    import nevergrad as ng
                    algo = NevergradSearch(optimizer=ng.optimizers.OnePlusOne)
                elif 'ZOOpt' == method:
                    from ray.tune.suggest.zoopt import ZOOptSearch
                    algo = ZOOptSearch(budget=num_samples * n_cpu)
                elif 'Ax' == method:
                    from ray.tune.suggest.ax import AxSearch
                    algo = AxSearch()
                elif 'HyperOpt' == method:
                    from ray.tune.suggest.hyperopt import HyperOptSearch
                    algo = HyperOptSearch()
                    scheduler = None
                if method != 'BOHB':
                    from ray.tune.schedulers import ASHAScheduler
                    scheduler = ASHAScheduler(
                        max_t=max_iter,
                        grace_period=1)
                analysis = tune.run(
                    train_breast_cancer,
                    metric="eval-logloss",
                    mode="min",
                    # You can add "gpu": 0.1 to allocate GPUs
                    resources_per_trial={"cpu": 1},
                    config=search_space, local_dir='logs/',
                    num_samples=num_samples * n_cpu,
                    time_budget_s=time_budget_s,
                    scheduler=scheduler, search_alg=algo)
            ray.shutdown()
            # # Load the best model checkpoint
            # import os
            # best_bst = xgb.Booster()
            # best_bst.load_model(os.path.join(analysis.best_checkpoint,
            #  "model.xgb"))
            best_trial = analysis.get_best_trial("eval-logloss", "min", "all")
            accuracy = 1. - best_trial.metric_analysis["eval-error"]["min"]
            logloss = best_trial.metric_analysis["eval-logloss"]["min"]
            logger.info(f"method={method}")
            logger.info(f"n_samples={num_samples*n_cpu}")
            logger.info(f"time={time.time()-start_time}")
            logger.info(f"Best model eval loss: {logloss:.4f}")
            logger.info(f"Best model total accuracy: {accuracy:.4f}")
            logger.info(f"Best model parameters: {best_trial.config}")


def test_nested():
    from flaml import tune
    search_space = {
        # test nested search space
        "cost_related": {
            "a": tune.randint(1, 8),
        },
        "b": tune.uniform(0.5, 1.0),
    }

    def simple_func(config):
        tune.report(metric=(config["cost_related"]["a"] - 4)**2
                    * (config["b"] - 0.7)**2)

    tune.run(
        simple_func,
        config=search_space,
        low_cost_partial_config={
            "cost_related": {"a": 1}
        },
        metric="metric",
        mode="min",
        local_dir='logs/',
        num_samples=-1,
        time_budget_s=1)


def test_xgboost_bs():
    _test_xgboost()


def test_xgboost_cfo():
    _test_xgboost('CFO')


def _test_xgboost_dragonfly():
    _test_xgboost('Dragonfly')


def _test_xgboost_skopt():
    _test_xgboost('SkOpt')


def _test_xgboost_nevergrad():
    _test_xgboost('Nevergrad')


def _test_xgboost_zoopt():
    _test_xgboost('ZOOpt')


def _test_xgboost_ax():
    _test_xgboost('Ax')


def __test_xgboost_hyperopt():
    _test_xgboost('HyperOpt')


def _test_xgboost_optuna():
    _test_xgboost('Optuna')


def _test_xgboost_asha():
    _test_xgboost('ASHA')


def _test_xgboost_bohb():
    _test_xgboost('BOHB')


if __name__ == "__main__":
    unittest.main()
