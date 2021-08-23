import time


def evaluation_fn(step, width, height):
    return (0.1 + width * step / 100)**(-1) + height * 0.1


def easy_objective(config):
    from ray import tune
    # Hyperparameters
    width, height = config["width"], config["height"]

    for step in range(config["steps"]):
        # Iterative training function - can be any arbitrary training procedure
        intermediate_score = evaluation_fn(step, width, height)
        # Feed the score back back to Tune.
        tune.report(iterations=step, mean_loss=intermediate_score)
        time.sleep(0.1)


def test_blendsearch_tune(smoke_test=True):
    try:
        from ray import tune
        from ray.tune.suggest import ConcurrencyLimiter
        from ray.tune.schedulers import AsyncHyperBandScheduler
        from ray.tune.suggest.flaml import BlendSearch
    except ImportError:
        print('ray[tune] is not installed, skipping test')
        return
    import numpy as np

    algo = BlendSearch()
    algo = ConcurrencyLimiter(algo, max_concurrent=4)
    scheduler = AsyncHyperBandScheduler()
    analysis = tune.run(
        easy_objective,
        metric="mean_loss",
        mode="min",
        search_alg=algo,
        scheduler=scheduler,
        num_samples=10 if smoke_test else 100,
        config={
            "steps": 100,
            "width": tune.uniform(0, 20),
            "height": tune.uniform(-100, 100),
            # This is an ignored parameter.
            "activation": tune.choice(["relu", "tanh"]),
            "test4": np.zeros((3, 1)),
        })

    print("Best hyperparameters found were: ", analysis.best_config)


if __name__ == "__main__":
    test_blendsearch_tune(False)
