#
# Run this file to download the human_eval dataset, and create a corresponding testbed scenario:
# (default: ../scenarios/human_eval_two_agents_gpt4.jsonl and ./scenarios/human_eval_two_agents_gpt35.jsonl)
#

import requests
import tarfile
import io
import json
import os
import re
import sys

URL = "https://people.eecs.berkeley.edu/~hendrycks/MATH.tar"

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

SCENARIO_DIR = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir))
TEMPLATES_DIR = os.path.join(SCENARIO_DIR, "Templates")
TASKS_DIR = os.path.join(SCENARIO_DIR, "Tasks")
DOWNLOADS_DIR = os.path.join(SCENARIO_DIR, "Downloads")

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
    """Download the MATH dataset (if not already downloaded).
    Return a JSON dictionary of selected problems."""

    selected_problems = dict()

    if not os.path.isdir(DOWNLOADS_DIR):
        os.mkdir(DOWNLOADS_DIR)

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
            content = tar.extractfile(member).read()
            selected_problems[member.name] = json.loads(content)

    return selected_problems


def create_jsonl(name, problems, template):
    """Creates a JSONL scenario file with a given name, dictionary of MATH problems, and template path."""

    # Create a task directory if it doesn't exist
    if not os.path.isdir(TASKS_DIR):
        os.mkdir(TASKS_DIR)

    # Create the jsonl file
    with open(os.path.join(TASKS_DIR, name + ".jsonl"), "wt") as fh:
        for item in problems.items():
            data = item[1]

            task_id = item[0].replace("MATH/", "").replace(".json", "").replace("/", "_")
            print(f"Converting: [{item[0]}] {task_id}")

            record = {
                "id": task_id,
                "template": template,
                "substitutions": {
                    "prompt.txt": {"__PROMPT__": data["problem"]},
                    "expected_answer.txt": {"__ANSWER__": data["solution"]},
                },
            }

            fh.write(json.dumps(record).strip() + "\n")


###############################################################################
def main():
    problems = download_math()

    # list all directories in the Templates directory
    # and populate a dictionary with the name and path
    templates = {}
    for entry in os.scandir(TEMPLATES_DIR):
        if entry.is_dir():
            templates[re.sub(r"\s", "", entry.name)] = entry.path

    for t in templates.items():
        create_jsonl(f"math_{t[0]}", problems, t[1])


if __name__ == "__main__" and __package__ is None:
    main()
