import os
import shutil
import sys
import re
from typing import Sequence


def default_scorer(instance_dir: str) -> bool:
    """
    returns True if the instance_dir has the expected ending pattern in the console_log.txt file
    """
    console_log = os.path.join(instance_dir, "console_log.txt")
    if os.path.isfile(console_log):
        with open(console_log, "rt") as fh:
            content = fh.read()
            # Use a regular expression to match the expected ending pattern
            has_final_answer = "FINAL ANSWER:" in content
            has_scenario_complete = "SCENARIO.PY COMPLETE !#!#" in content
            has_run_complete = "RUN.SH COMPLETE !#!#" in content
            # if so, return False
            last_10_lines = content.splitlines()[-10:]
            last_10_lines = "\n".join(last_10_lines)
            has_error_in_last_10_lines = "openai.RateLimitError: Error code: 429" in last_10_lines
            has_all = has_final_answer and has_scenario_complete and has_run_complete and not has_error_in_last_10_lines
            if not has_all:
                print(content)
            return has_all
    return False


def delete_folders_with_missing_results(runlogs_path: str):
    deleted_folders = 0

    for task_id in os.listdir(runlogs_path):
        task_path = os.path.join(runlogs_path, task_id)

        if not os.path.isdir(task_path):
            continue

        instance = 0
        has_missing_results = False

        while True:
            instance_dir = os.path.join(task_path, str(instance))
            if not os.path.isdir(instance_dir):
                if instance == 0:
                    print(f"Empty folder: {task_path}")
                    has_missing_results = True
                break
            if not default_scorer(instance_dir):
                has_missing_results = True
                break

            instance += 1
        if has_missing_results:
            print(f"Missing Results in : {task_path}")
            user_confirmation = input("Press 1 to delete, anything else to skip...")
            if user_confirmation == "1":
                shutil.rmtree(task_path)
                print(f"Deleted folder: {task_path}")
                deleted_folders += 1
            else:
                print(f"Skipping folder: {task_path}")

    print(f"Total folders deleted: {deleted_folders}")



def remove_missing_cli(args: Sequence[str]) -> None:
    invocation_cmd = args[0]
    args = args[1:]
    runlogs_path = args[0]
    if len(args) != 1:
        print("Usage: agbench remove_missing <path_to_runlogs>")
        sys.exit(1)
    if not os.path.isdir(runlogs_path):
        print(f"Error: '{runlogs_path}' is not a valid directory.")
        sys.exit(1)
    input("Did you modify the default_scorer function to match the expected ending pattern? Press Enter to continue...")

    delete_folders_with_missing_results(runlogs_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python remove_missing.py <path_to_runlogs>")
        sys.exit(1)

    runlogs_path = sys.argv[1]
    if not os.path.isdir(runlogs_path):
        print(f"Error: '{runlogs_path}' is not a valid directory.")
        sys.exit(1)
    input("Did you modify the default_scorer function to match the expected ending pattern? Press Enter to continue...")

    delete_folders_with_missing_results(runlogs_path)

