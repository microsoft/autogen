import numpy as np
from flaml import tune
from flaml.tune import INCUMBENT_RESULT


def rosenbrock_function(config: dict):
    funcLoss = 50
    for key, value in config.items():
        if key in ["x1", "x2", "x3", "x4", "x5"]:
            funcLoss += value**2 - 10 * np.cos(2 * np.pi * value)
    if INCUMBENT_RESULT in config.keys():
        print("----------------------------------------------")
        print("incumbent result", config[INCUMBENT_RESULT])
        print("----------------------------------------------")

    return {"funcLoss": funcLoss}


def test_record_incumbent(method="BlendSearch"):

    if method != "CFOCat":
        search_space = {
            "x1": tune.randint(1, 9),
            "x2": tune.randint(1, 9),
            "x3": tune.randint(1, 9),
            "x4": tune.randint(1, 9),
            "x5": tune.randint(1, 9),
        }
    else:
        search_space = {
            "x1": tune.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
            "x2": tune.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
            "x3": tune.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
            "x4": tune.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
            "x5": tune.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
        }

    max_iter = 100
    num_samples = 128
    time_budget_s = 1
    n_cpu = 1

    if method == "BlendSearch":
        tune.run(
            evaluation_function=rosenbrock_function,
            config=search_space,
            verbose=0,
            metric="funcLoss",
            mode="min",
            max_resource=max_iter,
            min_resource=1,
            local_dir="logs/",
            num_samples=num_samples * n_cpu,
            time_budget_s=time_budget_s,
            use_incumbent_result_in_evaluation=True,
        )
        return
    elif method == "CFO":
        from flaml import CFO

        algo = CFO(
            use_incumbent_result_in_evaluation=True,
        )
    elif method == "CFOCat":
        from flaml.tune.searcher.cfo_cat import CFOCat

        algo = CFOCat(
            use_incumbent_result_in_evaluation=True,
        )
    else:
        raise NotImplementedError
    tune.run(
        evaluation_function=rosenbrock_function,
        metric="funcLoss",
        mode="min",
        config=search_space,
        local_dir="logs/",
        num_samples=num_samples * n_cpu,
        time_budget_s=time_budget_s,
        search_alg=algo,
    )


if __name__ == "__main__":
    test_record_incumbent(method="BlendSearch")
