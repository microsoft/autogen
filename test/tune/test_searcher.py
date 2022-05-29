from time import sleep
import numpy as np

try:
    from ray import __version__ as ray_version

    assert ray_version >= "1.10.0"
    from ray.tune import sample

    use_ray = True
except (ImportError, AssertionError):
    from flaml.tune import sample

    use_ray = False


def define_search_space(trial):
    trial.suggest_float("a", 6, 8)
    trial.suggest_float("b", 1e-4, 1e-2, log=True)


def long_define_search_space(trial):
    sleep(1)
    return 3


def wrong_define_search_space(trial):
    return {1: 1}


def test_searcher():
    from flaml.searcher.suggestion import OptunaSearch, Searcher, ConcurrencyLimiter
    from flaml.searcher.blendsearch import BlendSearch, CFO, RandomSearch
    from flaml.tune import sample as flamlsample

    searcher = Searcher()
    try:
        searcher = Searcher(metric=1, mode=1)
    except ValueError:
        # Mode must either be a list or string
        pass
    searcher = Searcher(metric=["m1", "m2"], mode=["max", "min"])
    searcher.set_search_properties(None, None, None)
    searcher.suggest = searcher.on_pause = searcher.on_unpause = lambda _: {}
    searcher.on_trial_complete = lambda trial_id, result, error: None
    searcher = ConcurrencyLimiter(searcher, max_concurrent=2, batch=True)
    searcher.on_trial_complete("t0")
    searcher.suggest("t1")
    searcher.suggest("t2")
    searcher.on_pause("t1")
    searcher.on_unpause("t1")
    searcher.suggest("t3")
    searcher.on_trial_complete("t1", {})
    searcher.on_trial_complete("t2", {})
    searcher.set_state({})
    print(searcher.get_state())
    import optuna

    config = {
        "a": optuna.distributions.UniformDistribution(6, 8),
        "b": optuna.distributions.LogUniformDistribution(1e-4, 1e-2),
    }
    searcher = OptunaSearch(["a", config["a"]], metric="m", mode="max")
    try:
        searcher.suggest("t0")
    except ValueError:
        # not enough values to unpack (expected 3, got 1)
        pass
    searcher = OptunaSearch(
        config,
        points_to_evaluate=[{"a": 6, "b": 1e-3}],
        evaluated_rewards=[{"m": 2}],
        metric="m",
        mode="max",
    )
    try:
        searcher.add_evaluated_point({}, None, error=True)
    except ValueError:
        # nconsistent parameters set() and distributions {'b', 'a'}.
        pass
    try:
        searcher.add_evaluated_point({"a", 1, "b", 0.01}, None, pruned=True)
    except AttributeError:
        # 'set' object has no attribute 'keys'
        pass
    try:
        searcher.add_evaluated_point(
            {"a": 1, "b": 0.01}, None, intermediate_values=[0.1]
        )
    except ValueError:
        # `value` is supposed to be set for a complete trial.
        pass
    try:
        searcher = OptunaSearch(config, points_to_evaluate=1)
    except TypeError:
        # points_to_evaluate expected to be a list, got <class 'int'>
        pass
    try:
        searcher = OptunaSearch(config, points_to_evaluate=[1])
    except TypeError:
        # points_to_evaluate expected to include list or dict
        pass
    try:
        searcher = OptunaSearch(config, points_to_evaluate=[{"a": 1}])
    except ValueError:
        # Dim of point {'a': 1} and parameter_names {'a': UniformDistribution(high=8.0, low=6.0), 'b': LogUniformDistribution(high=0.01, low=0.0001)} do not match.
        pass
    try:
        searcher = OptunaSearch(
            config, points_to_evaluate=[{"a": 1, "b": 0.01}], evaluated_rewards=1
        )
    except TypeError:
        # valuated_rewards expected to be a list, got <class 'int'>.
        pass
    try:
        searcher = OptunaSearch(
            config, points_to_evaluate=[{"a": 1, "b": 0.01}], evaluated_rewards=[1, 2]
        )
    except ValueError:
        # Dim of evaluated_rewards [1, 2] and points_to_evaluate [{'a': 1, 'b': 0.01}] do not match.
        pass
    config = {"a": sample.uniform(6, 8), "b": sample.loguniform(1e-4, 1e-2)}
    OptunaSearch.convert_search_space({"a": 1})
    try:
        OptunaSearch.convert_search_space({"a": {"grid_search": [1, 2]}})
    except ValueError:
        # Grid search parameters cannot be automatically converted to an Optuna search space.
        pass
    OptunaSearch.convert_search_space({"a": flamlsample.quniform(1, 3, 1)})
    try:
        searcher = OptunaSearch(
            config,
            points_to_evaluate=[{"a": 6, "b": 1e-3}],
            evaluated_rewards=[{"m": 2}],
            metric="m",
            mode="max",
        )
    except ValueError:
        # Optuna search does not support parameters of type `Float` with samplers of type `_Uniform`
        pass
    searcher = OptunaSearch(long_define_search_space, metric="m", mode="min")
    try:
        searcher.suggest("t0")
    except TypeError:
        # The return value of the define-by-run function passed in the `space` argument should be either None or a `dict` with `str` keys.
        pass
    searcher = OptunaSearch(wrong_define_search_space, metric="m", mode="min")
    try:
        searcher.suggest("t0")
    except TypeError:
        # At least one of the keys in the dict returned by the define-by-run function passed in the `space` argument was not a `str`.
        pass
    searcher = OptunaSearch(metric="m", mode="min")
    try:
        searcher.suggest("t0")
    except RuntimeError:
        # Trying to sample a configuration from OptunaSearch, but no search space has been defined.
        pass
    try:
        searcher.add_evaluated_point({}, 1)
    except RuntimeError:
        # Trying to sample a configuration from OptunaSearch, but no search space has been defined.
        pass
    searcher = OptunaSearch(define_search_space)
    try:
        searcher.suggest("t0")
    except RuntimeError:
        # Trying to sample a configuration from OptunaSearch, but the `metric` (None) or `mode` (None) parameters have not been set.
        pass
    try:
        searcher.add_evaluated_point({}, 1)
    except RuntimeError:
        # Trying to sample a configuration from OptunaSearch, but the `metric` (None) or `mode` (None) parameters have not been set.
        pass
    searcher = OptunaSearch(
        define_search_space,
        points_to_evaluate=[{"a": 6, "b": 1e-3}],
        # evaluated_rewards=[{'m': 2}], metric='m', mode='max'
        mode="max",
    )
    # searcher = OptunaSearch()
    # searcher.set_search_properties('m', 'min', define_search_space)
    searcher.set_search_properties("m", "min", config)
    searcher.suggest("t1")
    searcher.on_trial_complete("t1", None, False)
    searcher.suggest("t2")
    searcher.on_trial_complete("t2", None, True)
    searcher.suggest("t3")
    searcher.on_trial_complete("t3", {"m": np.nan})
    searcher.save("test/tune/optuna.pickle")
    searcher.restore("test/tune/optuna.pickle")
    try:
        searcher = BlendSearch(
            metric="m", global_search_alg=searcher, metric_constraints=[("c", "<", 1)]
        )
    except AssertionError:
        # sign of metric constraints must be <= or >=.
        pass
    searcher = BlendSearch(
        metric="m",
        global_search_alg=searcher,
        metric_constraints=[("c", "<=", 1)],
        points_to_evaluate=[{"a": 1, "b": 0.01}],
    )
    searcher.set_search_properties(
        metric="m2", config=config, setting={"time_budget_s": 0}
    )
    c = searcher.suggest("t1")
    print("t1", c)
    c = searcher.suggest("t2")
    print("t2", c)
    c = searcher.suggest("t3")
    print("t3", c)
    searcher.on_trial_complete("t1", {"config": c}, True)
    searcher.on_trial_complete("t2", {"config": c, "m2": 1, "c": 2, "time_total_s": 1})
    config1 = config.copy()
    config1["_choice_"] = 0
    searcher._expand_admissible_region(
        lower={"root": [{"a": 0.5}, {"a": 0.4}]},
        upper={"root": [{"a": 0.9}, {"a": 0.8}]},
        space={"root": config1},
    )
    searcher = CFO(
        metric="m",
        mode="min",
        space=config,
        points_to_evaluate=[{"a": 7, "b": 1e-3}, {"a": 6, "b": 3e-4}],
        evaluated_rewards=[1, 1],
    )
    searcher.suggest("t1")
    searcher.suggest("t2")
    searcher.on_trial_result("t3", {})
    c = searcher.generate_parameters(1)
    searcher.receive_trial_result(1, c, {"default": 0})
    searcher.update_search_space(
        {
            "a": {
                "_value": [1, 2],
                "_type": "choice",
            },
            "b": {
                "_value": [1, 3],
                "_type": "randint",
            },
            "c": {
                "_value": [0.1, 3],
                "_type": "uniform",
            },
            "d": {
                "_value": [2, 8, 2],
                "_type": "quniform",
            },
            "e": {
                "_value": [2, 8],
                "_type": "loguniform",
            },
            "f": {
                "_value": [2, 8, 2],
                "_type": "qloguniform",
            },
            "g": {
                "_value": [0, 2],
                "_type": "normal",
            },
            "h": {
                "_value": [0, 2, 2],
                "_type": "qnormal",
            },
        }
    )
    np.random.seed(7654321)
    searcher = RandomSearch(
        space=config,
        points_to_evaluate=[{"a": 7, "b": 1e-3}, {"a": 6, "b": 3e-4}],
    )
    print(searcher.suggest("t1"))
    print(searcher.suggest("t2"))
    print(searcher.suggest("t3"))
    print(searcher.suggest("t4"))
    searcher.on_trial_complete({"t1"}, {})
    searcher.on_trial_result({"t2"}, {})
    np.random.seed(654321)
    searcher = RandomSearch(
        space=config,
        points_to_evaluate=[{"a": 7, "b": 1e-3}, {"a": 6, "b": 3e-4}],
    )
    print(searcher.suggest("t1"))
    print(searcher.suggest("t2"))
    print(searcher.suggest("t3"))
    searcher = RandomSearch(space={})
    print(searcher.suggest("t1"))
    searcher = BlendSearch(space={})
    print(searcher.suggest("t1"))
    from flaml import tune

    tune.run(lambda x: 1, config={}, use_ray=use_ray)


def test_no_optuna():
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "optuna"])
    import flaml.searcher.suggestion

    subprocess.check_call([sys.executable, "-m", "pip", "install", "optuna==2.8.0"])
