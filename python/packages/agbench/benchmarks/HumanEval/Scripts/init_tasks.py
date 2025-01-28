#
# Run this file to download the human_eval dataset, and create a corresponding testbed scenario:
# (default: ../scenarios/human_eval_two_agents_gpt4.jsonl and ./scenarios/human_eval_two_agents_gpt35.jsonl)
#

import base64
import gzip
import io
import json
import os
import re

import requests

URL = "https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl.gz"

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

SCENARIO_DIR = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir))
TEMPLATES_DIR = os.path.join(SCENARIO_DIR, "Templates")
TASKS_DIR = os.path.join(SCENARIO_DIR, "Tasks")

# A selected subset of HumanEval problems to work with during development

# Deprecated 2/5/2024 -- Use subsample instead
REDUCED_SET = [
    "HumanEval/2",
    "HumanEval/26",
    "HumanEval/32",
    "HumanEval/33",
    "HumanEval/36",
    "HumanEval/38",
    "HumanEval/41",
    "HumanEval/50",
    "HumanEval/56",
    "HumanEval/65",
    "HumanEval/67",
    "HumanEval/84",
    "HumanEval/85",
    "HumanEval/86",
    "HumanEval/89",
    "HumanEval/99",
    "HumanEval/104",
    "HumanEval/113",
    "HumanEval/115",
    "HumanEval/120",
    "HumanEval/124",
    "HumanEval/126",
    "HumanEval/132",
    "HumanEval/135",
    "HumanEval/140",
    "HumanEval/146",
]


def download_human_eval():
    """Download the HumanEval dataset, un-gzips it, and returns a list of its parsed JSON objects."""

    # Send a HTTP request to the URL of the file
    response = requests.get(URL)

    # Ensure we raise an error if the download failed
    response.raise_for_status()

    # Create a BytesIO object from the response content
    buffer = io.BytesIO(response.content)

    # Read the file, line by line, populating a list of parsed JSON objects
    results = []
    with gzip.GzipFile(fileobj=buffer) as f_in:
        for line in f_in:
            # Parse each line as JSON
            results.append(json.loads(line))

    return results


def create_jsonl(name, tasks, template):
    """Creates a JSONL scenario file with a given name, list of HumanEval tasks, and template path."""

    # Create a task directory if it doesn't exist
    if not os.path.isdir(TASKS_DIR):
        os.mkdir(TASKS_DIR)

    # Create the jsonl file
    with open(os.path.join(TASKS_DIR, name + ".jsonl"), "wt") as fh:
        for task in tasks:
            print(f"Converting: [{name}] {task['task_id']}")

            record = {
                "id": task["task_id"].replace("/", "_"),
                "template": template,
                "substitutions": {
                    "scenario.py": {"__ENTRY_POINT__": task["entry_point"]},
                    "prompt.txt": {"__PROMPT__": task["prompt"]},
                    "unit_tests.py": {"__TEST__": task["test"]},
                },
            }

            fh.write(json.dumps(record).strip() + "\n")


###############################################################################
def main():
    human_eval = download_human_eval()
    # Deprecated: reduced_human_eval = [t for t in human_eval if t["task_id"] in REDUCED_SET]

    # list all directories in the Templates directory
    # and populate a dictionary with the name and path
    templates = {}
    for entry in os.scandir(TEMPLATES_DIR):
        if entry.is_dir():
            templates[re.sub(r"\s", "", entry.name)] = entry.path

    # Create the various combinations of [models] x [templates]
    for t in templates.items():
        create_jsonl(f"human_eval_{t[0]}", human_eval, t[1])
        # Deprecated: create_jsonl(f"r_human_eval_{t[0]}", reduced_human_eval, t[1])


if __name__ == "__main__" and __package__ is None:
    main()
