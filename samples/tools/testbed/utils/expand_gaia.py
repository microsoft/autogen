#
# Run this file to download the human_eval dataset, and create a corresponding testbed scenario:
# (default: ../scenarios/human_eval_two_agents_gpt4.jsonl and ./scenarios/human_eval_two_agents_gpt35.jsonl)
#

import json
import os
import sys
import shutil

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)


def create_jsonl(name, tasks, template, model):
    """Creates a JSONL scenario file with a given name, list of HumanEval tasks, template path, and model."""

    scenarios_dir = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir, "scenarios", "GAIA"))

    with open(os.path.join(scenarios_dir, name + ".jsonl"), "wt") as fh:
        for task in tasks:
            print(f"Converting: [{name}] {task['task_id']}")

            record = {
                "id": task["task_id"],
                "template": template,
                "substitutions": {
                    "scenario.py": {
                        "__MODEL__": model,
                        "__FILE_NAME__": task["file_name"],
                        "__PROMPT__": task["Question"],
                    },
                    "scenario_init.sh": {"__FILE_NAME__": task["file_name"]},
                    "expected_answer.txt": {"__EXPECTED_ANSWER__": task["Final answer"]},
                },
            }

            fh.write(json.dumps(record).strip() + "\n")


###############################################################################
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"SYNTAX: python {SCRIPT_NAME} [path to GIA repository]")

    # Copy the relevant GAIA files
    gaia_path = os.path.realpath(sys.argv[1])

    gaia_validation_files = os.path.join(gaia_path, "2023", "validation")
    gaia_test_files = os.path.join(gaia_path, "2023", "test")

    if not os.path.isdir(gaia_validation_files) or not os.path.isdir(gaia_test_files):
        sys.exit(f"Error: '{gaia_path}' does not appear to be a copy of the GAIA repository.")

    gaia_merged_files = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir, "scenarios", "GAIA", "GAIA_Files"))

    shutil.copytree(
        gaia_validation_files, gaia_merged_files, ignore=shutil.ignore_patterns("metadata.jsonl"), dirs_exist_ok=True
    )
    shutil.copytree(
        gaia_test_files, gaia_merged_files, ignore=shutil.ignore_patterns("metadata.jsonl"), dirs_exist_ok=True
    )

    # Load the GAIA data
    gaia_validation_tasks = []
    with open(os.path.join(gaia_validation_files, "metadata.jsonl")) as fh:
        for line in fh:
            gaia_validation_tasks.append(json.loads(line))

    models = {
        "gpt4": "gpt-4",
    }

    templates = {
        "two_agents": "Templates/DefaultTwoAgents",
    }

    # Create necessary symlinks
    for t in templates.items():
        template_dir = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir, "scenarios", "GAIA", t[1]))
        try:
            os.symlink(gaia_merged_files, os.path.join(template_dir, "gaia_files"))
        except FileExistsError:
            pass

    # Create the various combinations of [models] x [templates]
    for m in models.items():
        for t in templates.items():
            create_jsonl(f"gaia_validation_{t[0]}_{m[0]}", gaia_validation_tasks, t[1], m[1])
