from functools import partial
import time


def evaluation_fn(step, width, height):
    return (0.1 + width * step / 100) ** (-1) + height * 0.1


def easy_objective(use_raytune, config):
    if use_raytune:
        from ray import tune
    else:
        from flaml import tune
    # Hyperparameters
    width, height = config["width"], config["height"]

    for step in range(config["steps"]):
        # Iterative training function - can be any arbitrary training procedure
        intermediate_score = evaluation_fn(step, width, height)
        # Feed the score back back to Tune.
        try:
            tune.report(iterations=step, mean_loss=intermediate_score)
        except StopIteration:
            return


def test_tune_scheduler(smoke_test=True, use_ray=True, use_raytune=False):
    import numpy as np
    from flaml.searcher.blendsearch import BlendSearch

    np.random.seed(100)
    easy_objective_custom_tune = partial(easy_objective, use_raytune)
    if use_raytune:
        try:
            from ray import tune
        except ImportError:
            print("ray[tune] is not installed, skipping test")
            return
        searcher = BlendSearch(
            space={
                "steps": 100,
                "width": tune.uniform(0, 20),
                "height": tune.uniform(-100, 100),
                # This is an ignored parameter.
                "activation": tune.choice(["relu", "tanh"]),
                "test4": np.zeros((3, 1)),
            }
        )
        analysis = tune.run(
            easy_objective_custom_tune,
            search_alg=searcher,
            metric="mean_loss",
            mode="min",
            num_samples=10 if smoke_test else 100,
            scheduler="asynchyperband",
            config={
                "steps": 100,
                "width": tune.uniform(0, 20),
                "height": tune.uniform(-100, 100),
                # This is an ignored parameter.
                "activation": tune.choice(["relu", "tanh"]),
                "test4": np.zeros((3, 1)),
            },
        )
    else:
        from flaml import tune

        searcher = BlendSearch(
            space={
                "steps": 100,
                "width": tune.uniform(0, 20),
                "height": tune.uniform(-100, 100),
                # This is an ignored parameter.
                "activation": tune.choice(["relu", "tanh"]),
                "test4": np.zeros((3, 1)),
            }
        )
        analysis = tune.run(
            easy_objective_custom_tune,
            search_alg=searcher,
            metric="mean_loss",
            mode="min",
            num_samples=10 if smoke_test else 100,
            scheduler="asynchyperband",
            resource_attr="iterations",
            max_resource=99,
            # min_resource=1,
            # reduction_factor=4,
            config={
                "steps": 100,
                "width": tune.uniform(0, 20),
                "height": tune.uniform(-100, 100),
                # This is an ignored parameter.
                "activation": tune.choice(["relu", "tanh"]),
                "test4": np.zeros((3, 1)),
            },
            use_ray=use_ray,
        )

    print("Best hyperparameters found were: ", analysis.best_config)
    print("best results", analysis.best_result)


if __name__ == "__main__":
    test_tune_scheduler(smoke_test=True, use_ray=True, use_raytune=True)
    test_tune_scheduler(smoke_test=True, use_ray=True)
    test_tune_scheduler(smoke_test=True, use_ray=False)
