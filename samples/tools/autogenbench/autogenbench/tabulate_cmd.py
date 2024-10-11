import argparse
import os
import sys

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

EXCLUDE_DIR_NAMES = ["__pycache__"]


def find_tabulate_module(search_dir, stop_dir=None):
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


def default_scorer(instance_dir, success_strings=SUCCESS_STRINGS):
    console_log = os.path.join(instance_dir, "console_log.txt")
    if os.path.isfile(console_log):
        with open(console_log, "rt") as fh:
            content = fh.read()
            for s in success_strings:
                if s in content:
                    return True
            return False
    else:
        return None


def default_tabulate(args, scorer=default_scorer, exclude_dir_names=EXCLUDE_DIR_NAMES):
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

    parsed_args = parser.parse_args(args)

    all_results = list()
    max_instances = 0

    for task_id in sorted(
        os.listdir(parsed_args.runlogs),
        key=lambda s: os.path.getmtime(os.path.join(parsed_args.runlogs, s)),
    ):
        if task_id in exclude_dir_names:
            continue

        task_path = os.path.join(parsed_args.runlogs, task_id)

        if not os.path.isdir(task_path):
            continue

        # Collect the results vector
        results = [task_id]

        instance = 0
        instance_dir = os.path.join(task_path, str(instance))
        while os.path.isdir(instance_dir):
            results.append(scorer(instance_dir))
            instance += 1
            instance_dir = os.path.join(task_path, str(instance))

        max_instances = max(max_instances, instance)

        # Buffer the results
        all_results.append(results)

    if parsed_args.csv:
        # Create a header
        header = ["Task Id"]
        for i in range(0, max_instances):
            header.append("Trial " + str(i) + " Success")

        print(",".join(header))
        for row in all_results:
            str_row = [f"{v}" if v is not None else "" for v in row]
            while len(str_row) < max_instances + 1:
                str_row.append("")
            print(",".join(str_row))

        # Print out alpha-version warning
        sys.stderr.write("\n" + warning + "\n\n")
    else:
        # Create a header
        header = ["\nTask Id"]
        for i in range(0, max_instances):
            header.append("Trial " + str(i) + "\nSuccess")

        # Create the footer
        def _count_equals(value, trial):
            count = 0
            for row in all_results:
                # Count missing
                if value is None:
                    if trial + 1 < len(row):
                        if row[trial + 1] is None:
                            count += 1
                    else:
                        count += 1
                # Count match
                elif trial + 1 < len(row) and row[trial + 1] == value:
                    count += 1
            return count

        footer = []
        footer_row = ["Successes"]
        for i in range(0, max_instances):
            footer_row.append(_count_equals(True, i))
        footer.append(footer_row)

        footer_row = ["Failures"]
        for i in range(0, max_instances):
            footer_row.append(_count_equals(False, i))
        footer.append(footer_row)

        footer_row = ["Missing"]
        for i in range(0, max_instances):
            footer_row.append(_count_equals(None, i))
        footer.append(footer_row)

        footer_row = ["Total"]
        for i in range(0, max_instances):
            footer_row.append(footer[0][i + 1] + footer[1][i + 1] + footer[2][i + 1])
        footer.append(footer_row)

        table = all_results.copy()
        table.append(tb.SEPARATING_LINE)
        table.extend(footer)

        print(tb.tabulate(table, headers=header))

        # Print out alpha-version warning
        sys.stderr.write("\n" + warning + "\n\n")


def tabulate_cli(args):
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
        default_tabulate([invocation_cmd] + args)
    else:
        sys.stderr.write(f"Using tabulation method defined in '{module_path}'\n\n")
        load_module(module_path).main([invocation_cmd] + args)
