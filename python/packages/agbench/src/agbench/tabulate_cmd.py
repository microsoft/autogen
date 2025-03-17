import argparse
import os
import re
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence

import pandas as pd
import tabulate as tb

from .load_module import load_module

# Figure out where everything is
SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

TABULATE_FILE = "custom_tabulate.py"

SUCCESS_STRINGS = [
    "ALL TESTS PASSED !#!#",
]

COMPLETED_STRINGS = [
    "SCENARIO.PY COMPLETE !#!#",
]

EXCLUDE_DIR_NAMES = ["__pycache__"]

TIMER_REGEX = r"RUNTIME:\s*([\d.]+) !#!#"


def find_tabulate_module(search_dir: str, stop_dir: Optional[str] = None) -> Optional[str]:
    """Hunt for the tabulate script."""

    search_dir = os.path.abspath(search_dir)
    if not os.path.isdir(search_dir):
        raise ValueError(f"'{search_dir}' is not a directory.")

    stop_dir = None if stop_dir is None else os.path.abspath(stop_dir)

    while True:
        path = os.path.join(search_dir, TABULATE_FILE)
        if os.path.isfile(path):
            return path

        path = os.path.join(search_dir, "Scripts", TABULATE_FILE)
        if os.path.isfile(path):
            return path

        path = os.path.join(search_dir, "scripts", TABULATE_FILE)
        if os.path.isfile(path):
            return path

        # Stop if we hit the stop_dir
        if search_dir == stop_dir:
            break

        # Stop if we hit the root
        parent_dir = os.path.abspath(os.path.join(search_dir, os.pardir))
        if parent_dir == search_dir:
            break

        search_dir = parent_dir

    return None


def default_scorer(instance_dir: str, success_strings: List[str] = SUCCESS_STRINGS) -> Optional[bool]:
    console_log = os.path.join(instance_dir, "console_log.txt")
    if os.path.isfile(console_log):
        with open(console_log, "rt") as fh:
            content = fh.read()

            # It succeeded
            for s in success_strings:
                if s in content:
                    return True

            # It completed without succeeding
            for s in COMPLETED_STRINGS:
                if s in content:
                    return False

            # Has not, or did not, complete
            return None
    else:
        return None


def default_timer(instance_dir: str, timer_regex: str = TIMER_REGEX) -> Optional[float]:
    console_log = os.path.join(instance_dir, "console_log.txt")
    if os.path.isfile(console_log):
        with open(console_log, "rt") as fh:
            content = fh.read()

            # It succeeded
            m = re.search(timer_regex, content)
            if m:
                return float(m.group(1))
            else:
                return None
    else:
        return None


ScorerFunc = Callable[[str], Optional[bool]]
TimerFunc = Callable[[str], Optional[float]]


def default_tabulate(
    args: List[str],
    scorer: ScorerFunc = default_scorer,
    timer: TimerFunc = default_timer,
    exclude_dir_names: List[str] = EXCLUDE_DIR_NAMES,
) -> None:
    invocation_cmd = args[0]
    args = args[1:]

    warning = f"CAUTION: '{invocation_cmd}' is in early preview and is not thoroughly tested.\nPlease do not cite values from these calculations in academic work without first inspecting and verifying the results in the run logs yourself."

    # Prepare the argument parser
    parser = argparse.ArgumentParser(
        prog=invocation_cmd,
        description=f"{invocation_cmd} will tabulate the results of a previous run.",
    )

    parser.add_argument(
        "runlogs",
        help="The path where the run's logs are stored.",
    )
    parser.add_argument(
        "-c",
        "--csv",
        action="store_true",
        help="Output the results in CSV format.",
    )

    parser.add_argument(
        "-e", "--excel", help="Output the results in Excel format. Please specify a path for the Excel file.", type=str
    )

    parsed_args = parser.parse_args(args)
    runlogs: str = parsed_args.runlogs

    all_results: List[Dict[str, Any]] = list()
    max_instances = 0

    for task_id in sorted(
        os.listdir(runlogs),
        key=lambda s: os.path.getmtime(os.path.join(runlogs, s)),
    ):
        if task_id in exclude_dir_names:
            continue

        task_path = os.path.join(runlogs, task_id)

        if not os.path.isdir(task_path):
            continue

        # Collect the results vector
        results: Dict[str, Any] = {"Task Id": task_id}

        # Collect the results for each instance.
        instance_dirs = sorted(
            os.listdir(task_path),
            key=lambda s: os.path.getmtime(os.path.join(task_path, s)),
        )
        instances = [int(d) for d in instance_dirs if d.isdigit()]

        for instance in instances:
            instance_dir = os.path.join(task_path, str(instance))
            results[f"Trial {instance} Success"] = scorer(instance_dir)
            results[f"Trial {instance} Time"] = timer(instance_dir)

        max_instances = max(instances)

        # Buffer the results
        all_results.append(results)

    num_instances = max_instances + 1

    # Pad the results to max_instances
    for result in all_results:
        for i in range(num_instances):
            if f"Trial {i} Success" not in result:
                result[f"Trial {i} Success"] = None
            if f"Trial {i} Time" not in result:
                result[f"Trial {i} Time"] = None

    # Create dataframe from results.
    df = pd.DataFrame(all_results)

    if parsed_args.csv:
        # Print out the dataframe in CSV format
        print(df.to_csv(index=False))
        # Print out alpha-version warning
        sys.stderr.write("\n" + warning + "\n\n")
    else:
        # Tabulate the results.
        print(tb.tabulate(df, headers="keys", tablefmt="simple"))  # type: ignore

        # Aggregate statistics for all tasks for each trials.
        print("\nSummary Statistics\n")
        score_columns = ["Trial " + str(i) + " Success" for i in range(num_instances)]
        # Count the number of successes when the value is True.
        successes = df[score_columns].apply(lambda x: x is True).sum(axis=0)  # type: ignore
        # Count the number of failures when the value is False.
        failures: pd.Series = df[score_columns].apply(lambda x: x is False).sum(axis=0)  # type: ignore
        # Count the number of missing
        missings = df[score_columns].isna().sum(axis=0)  # type: ignore
        # Count the total number of instances
        totals = successes + failures + missings  # type: ignore
        # Calculate the average success rates
        avg_success_rates = successes / (successes + failures)  # type: ignore
        time_columns = ["Trial " + str(i) + " Time" for i in range(num_instances)]  # type: ignore
        # Count the total time of non-null values
        total_times = df[time_columns].sum(axis=0, skipna=True)  # type: ignore
        # Calculate the average time of non-null values
        avg_times = df[time_columns].mean(axis=0, skipna=True)  # type: ignore

        # Create a per-trial summary dataframe
        trial_df = pd.DataFrame(
            {
                "Successes": list(successes),  # type: ignore
                "Failures": list(failures),  # type: ignore
                "Missing": list(missings),  # type: ignore
                "Total": list(totals),  # type: ignore
                "Average Success Rate": list(avg_success_rates),  # type: ignore
                "Average Time": list(avg_times),  # type: ignore
                "Total Time": list(total_times),  # type: ignore
            },
            index=[f"Trial {i}" for i in range(num_instances)],
        )
        # Print out the per-trial summary dataframe.
        print(tb.tabulate(trial_df, headers="keys", tablefmt="simple"))  # type: ignore

        # Aggregate statistics across tasks for all trials.
        # At least one success for each trial, averaged across tasks.
        average_at_least_one_success = df[score_columns].any(axis=1).mean(skipna=True)  # type: ignore
        # All successes for each trial
        average_all_successes = df[score_columns].all(axis=1).mean(skipna=True)  # type: ignore

        # Create a dataframe
        trial_aggregated_df = pd.DataFrame(
            {
                "At Least One Success": [average_at_least_one_success],  # type: ignore
                "All Successes": [average_all_successes],  # type: ignore
            },
            index=["Trial Aggregated"],
        )
        # Print out the trial-aggregated dataframe.
        print(tb.tabulate(trial_aggregated_df, headers="keys", tablefmt="simple"))  # type: ignore

        # Print out alpha-version warning
        sys.stderr.write("\n" + warning + "\n\n")


def tabulate_cli(args: Sequence[str]) -> None:
    invocation_cmd = args[0]
    args = args[1:]

    # We won't assume much about the arguments, letting the dynamically-loaded
    # tabulate modules parse the arguments however they want. But, we will use
    # bare arguments (not starting a "-"), to help us find what module to load.
    module_path = find_tabulate_module(os.getcwd(), stop_dir=os.getcwd())
    for arg in reversed(args):
        if module_path is not None:
            break
        if arg.startswith("-"):
            continue
        module_path = find_tabulate_module(arg)

    # Load the module and hand over control
    if module_path is None:
        sys.stderr.write("Using default tabulation method.\n\n")
        default_tabulate([invocation_cmd] + list(args))
    else:
        sys.stderr.write(f"Using tabulation method defined in '{module_path}'\n\n")
        load_module(module_path).main([invocation_cmd] + list(args))
