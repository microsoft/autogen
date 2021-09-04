from flaml.searcher.blendsearch import CFO
import numpy as np
try:
    from ray import __version__ as ray_version
    assert ray_version >= '1.0.0'
    from ray.tune import sample
except (ImportError, AssertionError):
    from flaml.tune import sample
    from flaml.searcher.suggestion import OptunaSearch, Searcher, ConcurrencyLimiter
    from flaml.searcher.blendsearch import BlendSearch

    def define_search_space(trial):
        trial.suggest_float("a", 6, 8)
        trial.suggest_float("b", 1e-4, 1e-2, log=True)

    def test_searcher():
        searcher = Searcher()
        searcher = Searcher(metric=['m1', 'm2'], mode=['max', 'min'])
        searcher.set_search_properties(None, None, None)
        searcher.suggest = searcher.on_pause = searcher.on_unpause = lambda _: {}
        searcher.on_trial_complete = lambda trial_id, result, error: None
        searcher = ConcurrencyLimiter(searcher, max_concurrent=2, batch=True)
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
        searcher = OptunaSearch(
            config, points_to_evaluate=[{"a": 6, "b": 1e-3}],
            evaluated_rewards=[{'m': 2}], metric='m', mode='max'
        )
        config = {
            "a": sample.uniform(6, 8),
            "b": sample.loguniform(1e-4, 1e-2)
        }
        searcher = OptunaSearch(
            config, points_to_evaluate=[{"a": 6, "b": 1e-3}],
            evaluated_rewards=[{'m': 2}], metric='m', mode='max'
        )
        searcher = OptunaSearch(
            define_search_space, points_to_evaluate=[{"a": 6, "b": 1e-3}],
            # evaluated_rewards=[{'m': 2}], metric='m', mode='max'
            mode='max'
        )
        searcher = OptunaSearch()
        # searcher.set_search_properties('m', 'min', define_search_space)
        searcher.set_search_properties('m', 'min', config)
        searcher.suggest('t1')
        searcher.on_trial_complete('t1', None, False)
        searcher.suggest('t2')
        searcher.on_trial_complete('t2', None, True)
        searcher.suggest('t3')
        searcher.on_trial_complete('t3', {'m': np.nan})
        searcher.save('test/tune/optuna.pickle')
        searcher.restore('test/tune/optuna.pickle')
        searcher = BlendSearch(
            metric="m",
            global_search_alg=searcher, metric_constraints=[("c", "<", 1)])
        searcher.set_search_properties(metric="m2", config=config)
        searcher.set_search_properties(config={"time_budget_s": 0})
        c = searcher.suggest('t1')
        searcher.on_trial_complete("t1", {"config": c}, True)
        c = searcher.suggest('t2')
        searcher.on_trial_complete(
            "t2", {"config": c, "m2": 1, "c": 2, "time_total_s": 1})
        config1 = config.copy()
        config1['_choice_'] = 0
        searcher._expand_admissible_region(
            lower={'root': [{'a': 0.5}, {'a': 0.4}]},
            upper={'root': [{'a': 0.9}, {'a': 0.8}]},
            space={'root': config1},
        )
        searcher = CFO(
            metric='m', mode='min', space=config,
            points_to_evaluate=[{'a': 7, 'b': 1e-3}, {'a': 6, 'b': 3e-4}],
            evaluated_rewards=[1, 1])
        searcher.suggest("t1")
        searcher.suggest("t2")
        searcher.on_trial_result('t3', {})
        c = searcher.generate_parameters(1)
        searcher.receive_trial_result(1, c, {'reward': 0})
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
                    "_value": [.1, 3],
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
