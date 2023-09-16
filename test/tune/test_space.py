from flaml import BlendSearch, CFO, tune


def test_define_by_run():
    from flaml.tune.space import (
        unflatten_hierarchical,
        normalize,
        indexof,
        complete_config,
    )

    space = {
        # Sample a float uniformly between -5.0 and -1.0
        "uniform": tune.uniform(-5, -1),
        # Sample a float uniformly between 3.2 and 5.4,
        # rounding to increments of 0.2
        "quniform": tune.quniform(3.2, 5.4, 0.2),
        # Sample a float uniformly between 0.0001 and 0.01, while
        # sampling in log space
        "loguniform": tune.loguniform(1e-4, 1e-2),
        # Sample a float uniformly between 0.0001 and 0.1, while
        # sampling in log space and rounding to increments of 0.00005
        "qloguniform": tune.qloguniform(1e-4, 1e-1, 5e-5),
        # Sample a random float from a normal distribution with
        # mean=10 and sd=2
        # "randn": tune.randn(10, 2),
        # Sample a random float from a normal distribution with
        # mean=10 and sd=2, rounding to increments of 0.2
        # "qrandn": tune.qrandn(10, 2, 0.2),
        # Sample a integer uniformly between -9 (inclusive) and 15 (exclusive)
        "randint": tune.randint(-9, 15),
        # Sample a random uniformly between -21 (inclusive) and 12 (inclusive (!))
        # rounding to increments of 3 (includes 12)
        "qrandint": tune.qrandint(-21, 12, 3),
        # Sample a integer uniformly between 1 (inclusive) and 10 (exclusive),
        # while sampling in log space
        "lograndint": tune.lograndint(1, 10),
        # Sample a integer uniformly between 2 (inclusive) and 10 (inclusive (!)),
        # while sampling in log space and rounding to increments of 2
        "qlograndint": tune.qlograndint(2, 10, 2),
        # Sample an option uniformly from the specified choices
        "choice": tune.choice(["a", "b", "c"]),
        "const": 5,
    }
    choice = {"nested": space}
    bs = BlendSearch(
        space={"c": tune.choice([choice])},
        low_cost_partial_config={"c": choice},
        metric="metric",
        mode="max",
    )
    print(indexof(bs._gs.space["c"], choice))
    print(indexof(bs._gs.space["c"], {"nested": {"const": 1}}))
    config = bs._gs.suggest("t1")
    print(config)
    config = unflatten_hierarchical(config, bs._gs.space)[0]
    print(config)
    print(normalize({"c": [choice]}, bs._gs.space, config, {}, False))
    space["randn"] = tune.randn(10, 2)
    cfo = CFO(
        space={"c": tune.choice([0, choice])},
        metric="metric",
        mode="max",
    )
    for i in range(5):
        cfo.suggest(f"t{i}")
    # print(normalize(config, bs._gs.space, config, {}, False))
    print(complete_config({}, cfo._ls.space, cfo._ls))
    # test hierarchical space with low_cost_partial_config
    bs = BlendSearch(
        space={"c": tune.choice([0, choice]), "randn": tune.randn(10, 2)},
        low_cost_partial_config={"randn": 10},
        metric="metric",
        mode="max",
    )
    tune.run(lambda config: {"metric": 1}, search_alg=bs)


def test_grid():
    from flaml.tune.searcher.variant_generator import (
        generate_variants,
        grid_search,
        TuneError,
        has_unresolved_values,
    )
    from flaml.tune import sample

    space = {
        "activation": grid_search(["relu", "tanh"]),
        "learning_rate": grid_search([1e-3, 1e-4, 1e-5]),
        "c": sample.choice([2, 3]),
    }
    for _, generated in generate_variants({"config": space}):
        config = generated["config"]
        print(config)
    for _, generated in generate_variants({"config": space}, True):
        config = generated["config"]
        print(config)
    space = {
        "activation": grid_search([{"c": sample.choice([2, 3])}]),
        "learning_rate": grid_search([1e-3, 1e-4, 1e-5]),
    }
    try:
        for _, generated in generate_variants({"config": space}, True):
            config = generated["config"]
            print(config)
    except ValueError:
        # The variable `('config', 'activation', 'c')` could not be unambiguously resolved to a single value.
        pass
    space = {
        "c": sample.choice([{"c1": sample.choice([1, 2])}]),
        "a": sample.randint(1, 10),
        "b": sample.choice([sample.uniform(10, 20), sample.choice([1, 2])]),
    }
    for _, generated in generate_variants({"config": space}):
        config = generated["config"]
        print(config)
    space = {"a": grid_search(3)}
    try:
        print(has_unresolved_values(space))
    except TuneError:
        # Grid search expected list of values, got: 3
        pass
