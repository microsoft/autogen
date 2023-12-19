#
# Run this file to download the human_eval dataset, and create a corresponding testbed scenario:
# (default: ../scenarios/human_eval_two_agents_gpt4.jsonl and ./scenarios/human_eval_two_agents_gpt35.jsonl)
#

import requests
import tarfile
import io
import json
import os
import sys

URL = "https://people.eecs.berkeley.edu/~hendrycks/MATH.tar"

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

SCENARIO_DIR = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir))
TEMPLATES_DIR = os.path.join(SCENARIO_DIR, "Templates")
TASKS_DIR = os.path.join(SCENARIO_DIR, "Tasks")
DOWNLOADS_DIR = os.path.join(SCENARIO_DIR, "Downloads")
PROBLEMS_DIR = os.path.join(DOWNLOADS_DIR, "SelectedProblems")

SELECTED_PROBLEMS = [
    "MATH/test/algebra/2144.json",
    "MATH/test/algebra/1997.json",
    "MATH/test/algebra/2072.json",
    "MATH/test/algebra/2137.json",
    "MATH/test/algebra/2557.json",
    "MATH/test/algebra/2045.json",
    "MATH/test/algebra/2499.json",
    "MATH/test/counting_and_probability/483.json",
    "MATH/test/intermediate_algebra/590.json",
    "MATH/test/prealgebra/1511.json",
    "MATH/test/intermediate_algebra/935.json",
    "MATH/test/prealgebra/808.json",
    "MATH/test/number_theory/233.json",
    "MATH/test/number_theory/960.json",
    "MATH/test/precalculus/551.json",
    "MATH/test/counting_and_probability/909.json",
    "MATH/test/algebra/2417.json",
]


def download_math():
    """Download the MATH dataset (if not already downloaded)."""

    if not os.path.isdir(DOWNLOADS_DIR):
        os.mkdir(DOWNLOADS_DIR)

    if not os.path.isdir(PROBLEMS_DIR):
        os.mkdir(PROBLEMS_DIR)

    tar_file = os.path.join(DOWNLOADS_DIR, "MATH.tar")

    if not os.path.isfile(tar_file):
        # Send a HTTP request to the URL
        response = requests.get(URL, stream=True)
        response.raise_for_status()

        # If the HTTP request returns a status code 200, proceed
        with open(tar_file, "wb") as fh:
            for chunk in response.iter_content(chunk_size=512):
                fh.write(chunk)

    # Extract selected problems
    tar = tarfile.open(tar_file)
    for member in tar.getmembers():
        if member.name in SELECTED_PROBLEMS:
            print(f"Extracting: {member.name}")
            fname = os.path.basename(member.name)
            content = tar.extractfile(member).read()
            with open(os.path.join(PROBLEMS_DIR, fname), "wb") as fh:
                fh.write(content)


def create_jsonl(name, tasks, template, model):
    """Creates a JSONL scenario file with a given name, list of HumanEval tasks, template path, and model."""

    # Create a task directory if it doesn't exist
    scenario_dir = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir))
    task_dir = os.path.join(scenario_dir, "Tasks")
    if not os.path.isdir(task_dir):
        os.mkdir(task_dir)

    # Create the jsonl file
    with open(os.path.join(task_dir, name + ".jsonl"), "wt") as fh:
        for task in tasks:
            print(f"Converting: [{name}] {task['task_id']}")

            record = {
                "id": task["task_id"].replace("/", "_"),
                "template": os.path.join(os.path.pardir, template),
                "substitutions": {
                    "scenario.py": {
                        "__MODEL__": model,
                        "__ENTRY_POINT__": task["entry_point"],
                        "__SELECTION_METHOD__": "auto",
                    },
                    "prompt.txt": {"__PROMPT__": task["prompt"]},
                    "coding/my_tests.py": {"__TEST__": task["test"]},
                },
            }

            fh.write(json.dumps(record).strip() + "\n")


###############################################################################
def main():
    download_math()
    sys.exit(0)

    # Create the various combinations of [models] x [templates]


#    for m in models.items():
#        for t in templates.items():
#            create_jsonl(f"human_eval_{t[0]}_{m[0]}", human_eval, t[1], m[1])
#            create_jsonl(f"r_human_eval_{t[0]}_{m[0]}", reduced_human_eval, t[1], m[1])


if __name__ == "__main__" and __package__ is None:
    main()
