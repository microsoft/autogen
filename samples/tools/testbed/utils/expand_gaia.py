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
SCENARIOS_DIR = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir, "scenarios", "GAIA"))


def create_jsonl(name, tasks, template, model):
    """Creates a JSONL scenario file with a given name, list of HumanEval tasks, template path, and model."""

    with open(os.path.join(SCENARIOS_DIR, name + ".jsonl"), "wt") as fh:
        for task in tasks:
            print(f"Converting: [{name}] {task['task_id']}")

            # Figure out what files we need to copy
            template_cp_list = [template]
            if len(task["file_name"].strip()) > 0:
                template_cp_list.append(
                    [
                        os.path.join("GAIA_Files", task["file_name"].strip()),
                        os.path.join("coding", task["file_name"].strip()),
                    ]
                )

            record = {
                "id": task["task_id"],
                "template": template_cp_list,
                "substitutions": {
                    "scenario.py": {
                        "__MODEL__": model,
                        "__FILE_NAME__": task["file_name"],
                        "__PROMPT__": task["Question"],
                    },
                    "expected_answer.txt": {"__EXPECTED_ANSWER__": task["Final answer"]},
                },
            }

            fh.write(json.dumps(record).strip() + "\n")


###############################################################################
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(
            f"SYNTAX: python {SCRIPT_NAME} [path to GIA repository]\n\nNote: to clone the GAIA repository, do 'git clone https://huggingface.co/datasets/gaia-benchmark/GAIA'"
        )

    # Copy the relevant GAIA files
    gaia_path = os.path.realpath(sys.argv[1])

    gaia_validation_files = os.path.join(gaia_path, "2023", "validation")
    gaia_test_files = os.path.join(gaia_path, "2023", "test")

    if not os.path.isdir(gaia_validation_files) or not os.path.isdir(gaia_test_files):
        sys.exit(f"Error: '{gaia_path}' does not appear to be a copy of the GAIA repository.")

    gaia_merged_files = os.path.realpath(os.path.join(SCENARIOS_DIR, "GAIA_Files"))

    shutil.copytree(
        gaia_validation_files, gaia_merged_files, ignore=shutil.ignore_patterns("metadata.jsonl"), dirs_exist_ok=True
    )
    shutil.copytree(
        gaia_test_files, gaia_merged_files, ignore=shutil.ignore_patterns("metadata.jsonl"), dirs_exist_ok=True
    )

    # Load the GAIA data
    gaia_validation_tasks = [[], [], []]
    with open(os.path.join(gaia_validation_files, "metadata.jsonl")) as fh:
        for line in fh:
            data = json.loads(line)
            gaia_validation_tasks[data["Level"] - 1].append(data)

    gaia_test_tasks = [[], [], []]
    with open(os.path.join(gaia_test_files, "metadata.jsonl")) as fh:
        for line in fh:
            data = json.loads(line)
            gaia_test_tasks[data["Level"] - 1].append(data)

    models = {
        "gpt4": "gpt-4",
    }

    templates = {
        "two_agents": "Templates/BasicTwoAgents",
    }

    # Add coding directories if needed (these are usually empty and left out of the repo)
    for template in templates.values():
        code_dir_path = os.path.join(SCENARIOS_DIR, template, "coding")
        if not os.path.isdir(code_dir_path):
            os.mkdir(code_dir_path)

    # Create the various combinations of [models] x [templates]
    for m in models.items():
        for t in templates.items():
            create_jsonl(f"gaia_validation_level_1__{t[0]}_{m[0]}", gaia_validation_tasks[0], t[1], m[1])
            create_jsonl(f"gaia_validation_level_2__{t[0]}_{m[0]}", gaia_validation_tasks[1], t[1], m[1])
            create_jsonl(f"gaia_validation_level_3__{t[0]}_{m[0]}", gaia_validation_tasks[2], t[1], m[1])
            create_jsonl(f"gaia_test_level_1__{t[0]}_{m[0]}", gaia_test_tasks[0], t[1], m[1])
            create_jsonl(f"gaia_test_level_2__{t[0]}_{m[0]}", gaia_test_tasks[1], t[1], m[1])
            create_jsonl(f"gaia_test_level_3__{t[0]}_{m[0]}", gaia_test_tasks[2], t[1], m[1])
