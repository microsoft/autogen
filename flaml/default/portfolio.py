import pandas as pd
import numpy as np
import argparse
from pathlib import Path
import json
from sklearn.preprocessing import RobustScaler
from flaml.default import greedy
from flaml.default.regret import load_result, build_regret
from flaml.version import __version__

regret_bound = 0.01


def config_predictor_tuple(tasks, configs, meta_features, regret_matrix):
    """Config predictor represented in tuple.

    The returned tuple consists of (meta_features, preferences, proc).

    Returns:
        meta_features_norm: A dataframe of normalized meta features, each column for a task.
        preferences: A dataframe of sorted configuration indicies by their performance per task (column).
        regret_matrix: A dataframe of the configuration(row)-task(column) regret matrix.
    """
    # pre-processing
    scaler = RobustScaler()
    meta_features_norm = meta_features.loc[tasks]  # this makes a copy
    meta_features_norm.loc[:, :] = scaler.fit_transform(meta_features_norm)

    proc = {
        "center": scaler.center_.tolist(),
        "scale": scaler.scale_.tolist(),
    }

    # best model for each dataset in training
    # choices = regret_matrix[tasks].loc[configs].reset_index(drop=True).idxmin()

    # break ties using the order in configs
    regret = (
        regret_matrix[tasks]
        .loc[configs]
        .reset_index(drop=True)
        .apply(lambda row: row.apply(lambda x: (x, row.name)), axis=1)
    )
    print(regret)
    preferences = pd.DataFrame(np.argsort(regret, axis=0), columns=regret.columns)
    print(preferences)
    return (meta_features_norm, preferences, proc)


def build_portfolio(meta_features, regret, strategy):
    """Build a portfolio from meta features and regret matrix.

    Args:
        meta_features: A dataframe of metafeatures matrix.
        regret: A dataframe of regret matrix.
        strategy: A str of the strategy, one of ("greedy", "greedy-feedback").
    """
    assert strategy in ("greedy", "greedy-feedback")
    if strategy == "greedy":
        portfolio = greedy.construct_portfolio(regret, None, regret_bound)
    elif strategy == "greedy-feedback":
        portfolio = greedy.construct_portfolio(regret, meta_features, regret_bound)
    if "default" not in portfolio and "default" in regret.index:
        portfolio += ["default"]
    return portfolio


def load_json(filename):
    """Returns the contents of json file filename."""
    with open(filename, "r") as f:
        return json.load(f)


def _filter(preference, regret):
    """Remove choices after default or have NaN regret."""
    try:
        last = regret.index.get_loc("default")  # len(preference) - 1
        preference = preference[: preference[preference == last].index[0] + 1]
    except KeyError:  # no "default"
        pass
    finally:
        regret = regret.reset_index(drop=True)
    preference = preference[regret[preference].notna().to_numpy()]
    # regret = regret[preference].reset_index(drop=True)
    # dup = regret[regret.duplicated()]
    # if not dup.empty:
    #     # break ties using the order in configs
    #     unique = dup.drop_duplicates()
    #     for u in unique:
    #         subset = regret == u
    #         preference[subset].sort_values(inplace=True)
    #     # raise ValueError(preference)
    return preference.tolist()


def serialize(configs, regret, meta_features, output_file, config_path):
    """Store to disk all information FLAML-metalearn needs at runtime.

    configs: names of model configs
    regret: regret matrix
    meta_features: task metafeatures
    output_file: filename
    config_path: path containing config json files
    """
    output_file = Path(output_file)
    # delete if exists
    try:
        output_file.unlink()
    except FileNotFoundError:
        pass

    meta_features_norm, preferences, proc = config_predictor_tuple(regret.columns, configs, meta_features, regret)
    portfolio = [load_json(config_path.joinpath(m + ".json")) for m in configs]
    regret = regret.loc[configs]

    meta_predictor = {
        "version": __version__,
        "meta_feature_names": list(meta_features.columns),
        "portfolio": portfolio,
        "preprocessing": proc,
        "neighbors": [
            {"features": x.tolist(), "choice": _filter(preferences[y], regret[y])}
            for x, y in zip(meta_features_norm.to_records(index=False), preferences.columns)
        ],
        "configsource": list(configs),
    }
    with open(output_file, "w+") as f:
        json.dump(meta_predictor, f, indent=4)
    return meta_predictor


# def analyze(regret_matrix, meta_predictor):
# tasks = regret_matrix.columns
# neighbors = meta_predictor["neighbors"]
# from sklearn.neighbors import NearestNeighbors

# nn = NearestNeighbors(n_neighbors=1)
# for i, task in enumerate(neighbors):
#     other_tasks = [j for j in range(len(neighbors)) if j != i]
#     # find the nn and the regret
#     nn.fit([neighbors[j]["features"] for j in other_tasks])
#     dist, ind = nn.kneighbors(
#         np.array(task["features"]).reshape(1, -1), return_distance=True
#     )
#     ind = other_tasks[int(ind.item())]
#     choice = int(neighbors[ind]["choice"][0])
#     r = regret_matrix.iloc[choice, i]
#     if r > regret_bound:
#         label = "outlier"
#     else:
#         label = "normal"
#     print(tasks[i], label, tasks[ind], "dist", dist, "regret", r)
#     # find the best model and the regret
#     regrets = regret_matrix.iloc[other_tasks, i]
#     best = regrets.min()
#     if best > regret_bound:
#         print(tasks[i], "best_regret", best, "task", regrets.idxmin())


def main():
    parser = argparse.ArgumentParser(description="Build a portfolio.")
    parser.add_argument("--strategy", help="One of {greedy, greedy-feedback}", default="greedy")
    parser.add_argument("--input", help="Input path")
    parser.add_argument("--metafeatures", help="CSV of task metafeatures")
    parser.add_argument("--exclude", help="One task name to exclude (for LOO purposes)")
    parser.add_argument("--output", help="Location to write portfolio JSON")
    parser.add_argument("--task", help="Task to merge portfolios", default="binary")
    parser.add_argument(
        "--estimator",
        help="Estimators to merge portfolios",
        default=["lgbm", "xgboost"],
        nargs="+",
    )
    args = parser.parse_args()

    meta_features = pd.read_csv(args.metafeatures, index_col=0).groupby(level=0).first()
    if args.exclude:
        meta_features.drop(args.exclude, inplace=True)

    baseline_best = None
    all_results = None
    for estimator in args.estimator:
        # produce regret
        all, baseline = load_result(f"{args.input}/{estimator}/results.csv", args.task, "result")
        regret = build_regret(all, baseline)
        regret = regret.replace(np.inf, np.nan).dropna(axis=1, how="all")

        if args.exclude:
            regret = regret.loc[[i for i in regret.index if args.exclude not in i]]
            regret = regret[[c for c in regret.columns if args.exclude not in c]]

        print(f"Regret matrix complete: {100 * regret.count().sum() / regret.shape[0] / regret.shape[1]}%")
        print(f"Num models considered: {regret.shape[0]}")

        configs = build_portfolio(meta_features, regret, args.strategy)
        meta_predictor = serialize(
            configs,
            regret,
            meta_features,
            f"{args.output}/{estimator}/{args.task}.json",
            Path(f"{args.input}/{estimator}"),
        )
        configsource = meta_predictor["configsource"]
        all = all.loc[configsource]
        all.rename({x: f"{estimator}/{x}" for x in regret.index.values}, inplace=True)
        baseline_best = baseline if baseline_best is None else pd.DataFrame({0: baseline_best, 1: baseline}).max(1)
        all_results = all if all_results is None else pd.concat([all_results, all])
        # analyze(regret, meta_predictor)
    regrets = build_regret(all_results, baseline_best)
    if len(args.estimator) > 1:
        meta_predictor = serialize(
            regrets.index,
            regrets,
            meta_features,
            f"{args.output}/all/{args.task}.json",
            Path(args.input),
        )


if __name__ == "__main__":
    # execute only if run as a script
    main()
