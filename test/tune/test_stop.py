from flaml import tune

n_trials = 0


def evaluate_config(config):
    global n_trials
    n_trials += 1
    if n_trials >= 10:
        return None
    metric = (round(config["x"]) - 85000) ** 2 - config["x"] / config["y"]
    return metric


def test_eval_stop():
    analysis = tune.run(
        evaluate_config,
        config={
            "x": tune.qloguniform(lower=1, upper=100000, q=1),
            "y": tune.qlograndint(lower=2, upper=100000, q=2),
        },
        num_samples=100,
        mode="max",
    )
    assert len(analysis.trials) == 10
