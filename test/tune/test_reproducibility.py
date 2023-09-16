from functools import partial


def _evaluation_fn(step, width, height):
    return (0.1 + width * step / 100) ** (-1) + height * 0.1


def _easy_objective(use_raytune, config):
    if use_raytune:
        from ray import tune
    else:
        from flaml import tune
    # Hyperparameters
    width, height = config["width"], config["height"]

    for step in range(config["steps"]):
        # Iterative training function - can be any arbitrary training procedure
        intermediate_score = _evaluation_fn(step, width, height)
        # Feed the score back back to Tune.
        try:
            tune.report(iterations=step, mean_loss=intermediate_score)
        except StopIteration:
            print("Trial stopped", step)
            return


def test_tune(externally_setup_searcher=False, use_ray=False, use_raytune=False):
    from flaml import tune
    from flaml.tune.searcher.blendsearch import BlendSearch

    easy_objective_custom_tune = partial(_easy_objective, use_raytune)
    search_space = {
        "steps": 100,
        "width": tune.uniform(0, 20),
        "height": tune.uniform(-100, 100),
    }
    if externally_setup_searcher is True:
        searcher = BlendSearch(
            space=search_space,
            time_budget_s=5,
            metric="mean_loss",
            mode="min",
        )
        assert searcher.cost_attr == "time_total_s", "when time_budget_s is provided, cost_attr should be time_total_s"

        searcher = BlendSearch(
            space=search_space,
            num_samples=10,
            metric="mean_loss",
            mode="min",
        )
        assert searcher.cost_attr is None, "when time_budget_s is not provided, cost_attr should be None."

        searcher = BlendSearch(
            space=search_space,
            num_samples=10,
            time_budget_s=5,
            metric="mean_loss",
            mode="min",
        )
        assert (
            searcher.cost_attr == "time_total_s"
        ), "As long as time_budget_s is provided and cost_attr not otherwise specified (i.e., using the default auto value), time_total_s is used as the cost_attr"

        searcher = BlendSearch(
            space=search_space,
            num_samples=10,
            time_budget_s=5,
            metric="mean_loss",
            mode="min",
            cost_attr=None,
        )
        assert (
            searcher.cost_attr is None
        ), "When the cost_attr is explicitly specified to be None, BS should use None as the cost_attr."

        searcher = BlendSearch(
            space=search_space,
            metric="mean_loss",
            mode="min",
        )
    elif externally_setup_searcher is False:
        searcher = None
    else:
        searcher = externally_setup_searcher

    analysis = tune.run(
        easy_objective_custom_tune,
        search_alg=searcher,
        metric="mean_loss",
        mode="min",
        num_samples=10,
        # time_budget_s=5,
        use_ray=use_ray,
        config=search_space,
    )

    print("Best hyperparameters found were: ", analysis.best_config)
    print("best results", analysis.best_result)
    print("best results", analysis.results)
    return analysis.best_config


def test_reproducibility():
    best_config_1 = test_tune()
    best_config_2 = test_tune()
    print(best_config_1)
    print(best_config_2)
    assert best_config_1 == best_config_2, "flaml.tune not reproducible"

    best_config_1 = test_tune(externally_setup_searcher=True)
    best_config_2 = test_tune(externally_setup_searcher=True)
    print(best_config_1)
    print(best_config_2)
    assert best_config_1 == best_config_2, "flaml.tune not reproducible when the searcher is set up externally"


def test_gs_reproducibility():
    from flaml import BlendSearch, tune

    def f(config):
        return {"m": 0.35}

    search_space = {"a": tune.randint(1, 100)}
    bs = BlendSearch(space=search_space, cost_attr=None)
    analysis1 = tune.run(f, search_alg=bs, num_samples=2, metric="m", mode="max")
    bs = BlendSearch(space=search_space, cost_attr=None)
    analysis2 = tune.run(f, search_alg=bs, num_samples=2, metric="m", mode="max")
    assert analysis1.trials[-1].config == analysis2.trials[-1].config


if __name__ == "__main__":
    test_reproducibility()
