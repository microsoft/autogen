import numpy as np
from flaml import tune
from flaml import BlendSearch, CFO


def _invalid_objective(config):
    # DragonFly uses `point`
    metric = "point" if "point" in config else "report"

    if config[metric] > 4:
        tune.report(float("inf"))
    elif config[metric] > 3:
        tune.report(float("-inf"))
    elif config[metric] > 2:
        tune.report(np.nan)
    else:
        tune.report(float(config[metric]) or 0.1)


config = {"report": tune.uniform(0.0, 5.0)}


def test_blendsearch():
    out = tune.run(
        _invalid_objective,
        search_alg=BlendSearch(
            points_to_evaluate=[
                {"report": 1.0},
                {"report": 2.1},
                {"report": 3.1},
                {"report": 4.1},
            ]
        ),
        config=config,
        metric="_metric",
        mode="max",
        num_samples=16,
    )

    best_trial = out.best_trial
    assert best_trial.config["report"] <= 2.0


def test_cfo():
    out = tune.run(
        _invalid_objective,
        search_alg=CFO(
            points_to_evaluate=[
                {"report": 1.0},
                {"report": 2.1},
                {"report": 3.1},
                {"report": 4.1},
            ]
        ),
        config=config,
        metric="_metric",
        mode="max",
        num_samples=16,
    )

    best_trial = out.best_trial
    assert best_trial.config["report"] <= 2.0
