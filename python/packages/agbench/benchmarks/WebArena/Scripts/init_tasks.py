#
# Run this file to download the human_eval dataset, and create a corresponding testbed scenario:
# (default: ../scenarios/human_eval_two_agents_gpt4.jsonl and ./scenarios/human_eval_two_agents_gpt35.jsonl)
#

import requests
import tarfile
import hashlib
import io
import json
import os
import re
import sys

URL = "https://raw.githubusercontent.com/web-arena-x/webarena/main/config_files/test.raw.json"

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

SCENARIO_DIR = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir))
TEMPLATES_DIR = os.path.join(SCENARIO_DIR, "Templates")
TASKS_DIR = os.path.join(SCENARIO_DIR, "Tasks")
DOWNLOADS_DIR = os.path.join(SCENARIO_DIR, "Downloads")


def download():
    """Download the WebArena dataset (if not already downloaded).
    Return a JSON list of problem instances."""

    if not os.path.isdir(DOWNLOADS_DIR):
        os.mkdir(DOWNLOADS_DIR)

    json_file = os.path.join(DOWNLOADS_DIR, "test.raw.json")

    if not os.path.isfile(json_file):
        # Send a HTTP request to the URL
        response = requests.get(URL, stream=True)
        response.raise_for_status()

        # If the HTTP request returns a status code 200, proceed
        with open(json_file, "wb") as fh:
            for chunk in response.iter_content(chunk_size=512):
                fh.write(chunk)

    # Load the problems
    problems = None
    with open(json_file, "rb") as fh:
        problems = json.load(fh)
    return problems


def create_jsonl(name, tasks, template):
    """Creates a JSONL scenario file with a given name, dictionary of MATH problems, and template path."""

    # Create a task directory if it doesn't exist
    if not os.path.isdir(TASKS_DIR):
        os.mkdir(TASKS_DIR)

    # Create the jsonl file
    prompt_fields = ["task_id", "intent_template_id", "sites", "require_login", "start_url", "geolocation", "intent"]
    with open(os.path.join(TASKS_DIR, name + ".jsonl"), "wt") as fh:
        for task in tasks:
            print(f"Converting: {name}, {task['task_id']}")

            task_prompt = {}
            for field in prompt_fields:
                task_prompt[field] = task[field]

            record = {
                "id": str(task["task_id"]),
                "template": [os.path.join(TEMPLATES_DIR, "Common"), template],
                "substitutions": {
                    "task_prompt.json.txt": {"__TASK_PROMPT__": json.dumps(task_prompt, indent=4)},
                    "full_task.json.txt": {"__FULL_TASK__": json.dumps(task, indent=4)},
                },
            }

            fh.write(json.dumps(record).strip() + "\n")


###############################################################################
def main():
    tasks = download()

    # list all directories in the Templates directory
    # and populate a dictionary with the name and path
    templates = {}
    for entry in os.scandir(TEMPLATES_DIR):
        if entry.is_dir():
            if entry.name == "Common":  # Skip the common template, which will be included in all
                continue
            templates[re.sub(r"\s", "", entry.name)] = entry.path

    # Divide the tasks by their websites and if they are validation or test
    page_groups = dict()
    for task in tasks:

        # We don't know how the intent ids are distributed, so hash them to get a uniform distribution
        template_hash = hashlib.md5(str(task["intent_template_id"]).encode("utf-8")).hexdigest()

        # The full hash will consist of 32 hexadecimal digits. We can get a 50/50 split by checking if the first digit is in the range (0-7) vs (8-F)
        task_set = "validation" if template_hash[0] in "01234567" else "test"

        key = task["sites"][0]
        if len(task["sites"]) > 1:
            key = "several_sites"
        key = task_set + "_" + key

        # key = "__".join(sorted([s for s in task["sites"]]))
        if key not in page_groups:
            page_groups[key] = list()
        page_groups[key].append(task)

    # Create the json files
    for t in templates.items():
        for pg in page_groups:
            create_jsonl(f"webarena__{pg}_{t[0]}", page_groups[pg], t[1])


if __name__ == "__main__" and __package__ is None:
    main()
