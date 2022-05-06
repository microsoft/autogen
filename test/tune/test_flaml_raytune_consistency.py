# import unittest
import numpy as np

# require: pip install flaml[blendsearch, ray]
# require: pip install flaml[ray]
import time
from flaml import tune


def evaluate_config(config):
    """evaluate a hyperparameter configuration"""
    # we uss a toy example with 2 hyperparameters
    metric = (round(config["x"]) - 85000) ** 2 - config["x"] / config["y"]
    # usually the evaluation takes an non-neglible cost
    # and the cost could be related to certain hyperparameters
    # in this example, we assume it's proportional to x
    time.sleep(config["x"] / 100000)
    # use tune.report to report the metric to optimize
    tune.report(metric=metric)


config_search_space = {
    "x": tune.lograndint(lower=1, upper=100000),
    "y": tune.randint(lower=1, upper=100000),
}

low_cost_partial_config = {"x": 1}


def setup_searcher(searcher_name):
    from flaml.searcher.blendsearch import BlendSearch, CFO, RandomSearch

    if "cfo" in searcher_name:
        searcher = CFO(
            space=config_search_space, low_cost_partial_config=low_cost_partial_config
        )
    elif searcher_name == "bs":
        searcher = BlendSearch(
            metric="metric",
            mode="min",
            space=config_search_space,
            low_cost_partial_config=low_cost_partial_config,
        )
    elif searcher_name == "random":
        searcher = RandomSearch(space=config_search_space)
    else:
        return None
    return searcher


def _test_flaml_raytune_consistency(
    num_samples=-1, max_concurrent_trials=1, searcher_name="cfo"
):
    try:
        from ray import tune as raytune
    except ImportError:
        print(
            "skip _test_flaml_raytune_consistency because ray tune cannot be imported."
        )
        return
    searcher = setup_searcher(searcher_name)
    analysis = tune.run(
        evaluate_config,  # the function to evaluate a config
        config=config_search_space,  # the search space
        low_cost_partial_config=low_cost_partial_config,  # a initial (partial) config with low cost
        metric="metric",  # the name of the metric used for optimization
        mode="min",  # the optimization mode, 'min' or 'max'
        num_samples=num_samples,  # the maximal number of configs to try, -1 means infinite
        time_budget_s=None,  # the time budget in seconds
        local_dir="logs/",  # the local directory to store logs
        search_alg=searcher,
        # verbose=0,          # verbosity
        # use_ray=True, # uncomment when performing parallel tuning using ray
    )
    flaml_best_config = analysis.best_config
    flaml_config_in_results = [v["config"] for v in analysis.results.values()]
    flaml_time_in_results = [v["time_total_s"] for v in analysis.results.values()]
    print(analysis.best_trial.last_result)  # the best trial's result

    searcher = setup_searcher(searcher_name)
    from ray.tune.suggest import ConcurrencyLimiter

    search_alg = ConcurrencyLimiter(searcher, max_concurrent_trials)
    analysis = raytune.run(
        evaluate_config,  # the function to evaluate a config
        config=config_search_space,
        metric="metric",  # the name of the metric used for optimization
        mode="min",  # the optimization mode, 'min' or 'max'
        num_samples=num_samples,  # the maximal number of configs to try, -1 means infinite
        local_dir="logs/",  # the local directory to store logs
        # max_concurrent_trials=max_concurrent_trials,
        # resources_per_trial={"cpu": max_concurrent_trials, "gpu": 0},
        search_alg=search_alg,
    )
    ray_best_config = analysis.best_config
    ray_config_in_results = [v["config"] for v in analysis.results.values()]
    ray_time_in_results = [v["time_total_s"] for v in analysis.results.values()]

    print(analysis.best_trial.last_result)  # the best trial's result
    print("time_total_s in flaml", flaml_time_in_results)  # the best trial's result
    print("time_total_s in ray", ray_time_in_results)  # the best trial's result

    print("best flaml", searcher_name, flaml_best_config)  # the best config
    print("ray best", searcher_name, ray_best_config)  # the best config

    print("flaml config in results", searcher_name, flaml_config_in_results)
    print("ray config in results", searcher_name, ray_config_in_results)
    assert ray_best_config == flaml_best_config, "best config should be the same"
    assert (
        flaml_config_in_results == ray_config_in_results
    ), "results from raytune and flaml should be the same"


def test_consistency():
    _test_flaml_raytune_consistency(
        num_samples=5, max_concurrent_trials=1, searcher_name="random"
    )
    _test_flaml_raytune_consistency(
        num_samples=5, max_concurrent_trials=1, searcher_name="cfo"
    )
    _test_flaml_raytune_consistency(
        num_samples=5, max_concurrent_trials=1, searcher_name="bs"
    )


if __name__ == "__main__":
    # unittest.main()
    test_consistency()
