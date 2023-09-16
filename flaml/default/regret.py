import argparse
from os import path
import pandas as pd


def build_regret(all, baseline):
    all = all[all.columns.intersection(baseline.index)]
    return baseline - all


def write_regret(regret, filename):
    regret.to_csv(filename)


def load_result(filename, task_type, metric):
    df = pd.read_csv(filename)
    df = df.loc[
        (df[metric].notnull()) & (df.type == task_type),
        ["task", "fold", "params", metric],
    ]
    df["params"] = df["params"].apply(lambda x: path.splitext(path.basename(eval(x)["_modeljson"]))[0])
    baseline = df.loc[df["task"] == df["params"], ["task", metric]].groupby("task").mean()[metric]
    df = df.pivot_table(index="params", columns="task", values=metric)
    return df, baseline


def main():
    parser = argparse.ArgumentParser(description="Build a regret matrix.")
    parser.add_argument("--result_csv", help="File of experiment results")
    parser.add_argument("--task_type", help="Type of task")
    parser.add_argument("--metric", help="Metric for calculating regret", default="result")
    parser.add_argument("--output", help="Location to write regret CSV to")
    args = parser.parse_args()

    all, baseline = load_result(args.result_csv, args.task_type, args.metric)
    regret = build_regret(all, baseline)
    write_regret(regret, args.output)


if __name__ == "__main__":
    # execute only if run as a script
    main()
