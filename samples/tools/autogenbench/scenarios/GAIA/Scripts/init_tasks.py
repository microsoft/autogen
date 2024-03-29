#
# Run this file to download the human_eval dataset, and create a corresponding testbed scenario:
# (default: ../scenarios/human_eval_two_agents_gpt4.jsonl and ./scenarios/human_eval_two_agents_gpt35.jsonl)
#

import json
import os
import sys
import re
from huggingface_hub import snapshot_download

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

SCENARIO_DIR = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir))
TEMPLATES_DIR = os.path.join(SCENARIO_DIR, "Templates")
TASKS_DIR = os.path.join(SCENARIO_DIR, "Tasks")
DOWNLOADS_DIR = os.path.join(SCENARIO_DIR, "Downloads")
REPO_DIR = os.path.join(DOWNLOADS_DIR, "GAIA")

SELECTED_TASKS = [
        "46719c30-f4c3-4cad-be07-d5cb21eee6bb",
        "9318445f-fe6a-4e1b-acbf-c68228c9906a",
        "935e2cff-ae78-4218-b3f5-115589b19dae",
        "3f57289b-8c60-48be-bd80-01f8099ca449",
        "72e110e7-464c-453c-a309-90a95aed6538",
        "840bfca7-4f7b-481a-8794-c560c340185d",
        "5a0c1adf-205e-4841-a666-7c3ef95def9d",
        "50ec8903-b81f-4257-9450-1085afd2c319",
        "9d191bce-651d-4746-be2d-7ef8ecadb9c2",
        "3cef3a44-215e-4aed-8e3b-b1e3f08063b7",
        "a0068077-79f4-461a-adfe-75c1a4148545",
        "305ac316-eef6-4446-960a-92d80d542f82",
        "4fc2f1ae-8625-45b5-ab34-ad4433bc21f8",
        "27d5d136-8563-469e-92bf-fd103c28b57c",
        "f918266a-b3e0-4914-865d-4faa564f1aef",
        "8e867cd7-cff9-4e6c-867a-ff5ddc2550be",
        "4b650a35-8529-4695-89ed-8dc7a500a498",
        "5cfb274c-0207-4aa7-9575-6ac0bd95d9b2",
    #
        "7dd30055-0198-452e-8c25-f73dbe27dcb8",
        "20194330-9976-4043-8632-f8485c6c71b2",
        "48eb8242-1099-4c26-95d4-ef22b002457a",
        "a7feb290-76bb-4cb7-8800-7edaf7954f2f",
        "2a649bb1-795f-4a01-b3be-9a01868dae73",
        "8b3379c0-0981-4f5b-8407-6444610cb212",
        "366e2f2b-8632-4ef2-81eb-bc3877489217",
        "ad37a656-079a-49f9-a493-7b739c9167d1",
        "ed58682d-bc52-4baa-9eb0-4eb81e1edacc",
        "54612da3-fd56-4941-80f4-5eb82330de25",
        "e0c10771-d627-4fd7-9694-05348e54ee36",
        "7cc4acfa-63fd-4acc-a1a1-e8e529e0a97f",
        "32102e3e-d12a-4209-9163-7b3a104efe5d",
        "f0f46385-fc03-4599-b5d3-f56496c3e69f",
        "076c8171-9b3b-49b9-a477-244d2a532826",
        "33d8ea3b-6c6b-4ff1-803d-7e270dea8a57",
        "71345b0a-9c7d-4b50-b2bf-937ec5879845",
        "e9a2c537-8232-4c3f-85b0-b52de6bcba99",
    #
        "ad2b4d70-9314-4fe6-bfbe-894a45f6055f",
        "50f58759-7bd6-406f-9b0d-5692beb2a926",
        "8131e2c0-0083-4265-9ce7-78c2d568425d",
        "00d579ea-0889-4fd9-a771-2c8d79835c8d",
        "e961a717-6b25-4175-8a68-874d28190ee4",
        "8d46b8d6-b38a-47ff-ac74-cda14cf2d19b",
        "56db2318-640f-477a-a82f-bc93ad13e882",
        "983bba7c-c092-455f-b6c9-7857003d48fc",
        "da52d699-e8d2-4dc5-9191-a2199e0b6a9b",
]


def download_gaia():
    """Download the GAIA benchmark from Hugging Face."""

    if not os.path.isdir(DOWNLOADS_DIR):
        os.mkdir(DOWNLOADS_DIR)

    """Download the GAIA dataset from Hugging Face Hub"""
    snapshot_download(
        repo_id="gaia-benchmark/GAIA",
        repo_type="dataset",
        local_dir=REPO_DIR,
        local_dir_use_symlinks=True,
    )


def create_jsonl(name, tasks, files_dir, template):
    """Creates a JSONL scenario file with a given name, and template path."""

    if not os.path.isdir(TASKS_DIR):
        os.mkdir(TASKS_DIR)

    with open(os.path.join(TASKS_DIR, name + ".jsonl"), "wt") as fh:
        for task in tasks:
            print(f"Converting: [{name}] {task['task_id']}")

            # Figure out what files we need to copy
            template_cp_list = [template]
            if len(task["file_name"].strip()) > 0:
                template_cp_list.append(
                    [
                        os.path.join(files_dir, task["file_name"].strip()),
                        os.path.join("coding", task["file_name"].strip()),
                    ]
                )

            record = {
                "id": task["task_id"],
                "template": template_cp_list,
                "substitutions": {
                    "scenario.py": {
                        "__FILE_NAME__": task["file_name"],
                    },
                    "expected_answer.txt": {"__EXPECTED_ANSWER__": task["Final answer"]},
                    "prompt.txt": {"__PROMPT__": task["Question"]},
                },
            }

            fh.write(json.dumps(record).strip() + "\n")


###############################################################################
def main():
    download_gaia()

    gaia_validation_files = os.path.join(REPO_DIR, "2023", "validation")
    gaia_test_files = os.path.join(REPO_DIR, "2023", "test")

    if not os.path.isdir(gaia_validation_files) or not os.path.isdir(gaia_test_files):
        sys.exit(f"Error: '{REPO_DIR}' does not appear to be a copy of the GAIA repository.")

    # Load the GAIA data
    gaia_validation_tasks = [[], [], []]
    gaia_selected_validation_tasks = []
    with open(os.path.join(gaia_validation_files, "metadata.jsonl")) as fh:
        for line in fh:
            data = json.loads(line)
            gaia_validation_tasks[data["Level"] - 1].append(data)
            if data["task_id"] in SELECTED_TASKS:
                gaia_selected_validation_tasks.append(data) 
            

    gaia_test_tasks = [[], [], []]
    with open(os.path.join(gaia_test_files, "metadata.jsonl")) as fh:
        for line in fh:
            data = json.loads(line)

            # A welcome message -- not a real task
            if data["task_id"] == "0-0-0-0-0":
                continue

            gaia_test_tasks[data["Level"] - 1].append(data)

    # list all directories in the Templates directory
    # and populate a dictionary with the name and path
    templates = {}
    for entry in os.scandir(TEMPLATES_DIR):
        if entry.is_dir():
            templates[re.sub(r"\s", "", entry.name)] = entry.path

    # Add coding directories if needed (these are usually empty and left out of the repo)
    for template in templates.values():
        code_dir_path = os.path.join(template, "coding")
        if not os.path.isdir(code_dir_path):
            os.mkdir(code_dir_path)

    # Create the various combinations of [models] x [templates]
    for t in templates.items():
        create_jsonl(
            f"gaia_validation_selected__{t[0]}",
            gaia_selected_validation_tasks,
            gaia_validation_files,
            t[1],
        )
        create_jsonl(
            f"gaia_validation_level_1__{t[0]}",
            gaia_validation_tasks[0],
            gaia_validation_files,
            t[1],
        )
        create_jsonl(
            f"gaia_validation_level_2__{t[0]}",
            gaia_validation_tasks[1],
            gaia_validation_files,
            t[1],
        )
        create_jsonl(
            f"gaia_validation_level_3__{t[0]}",
            gaia_validation_tasks[2],
            gaia_validation_files,
            t[1],
        )
        create_jsonl(
            f"gaia_test_level_1__{t[0]}",
            gaia_test_tasks[0],
            gaia_test_files,
            t[1],
        )
        create_jsonl(
            f"gaia_test_level_2__{t[0]}",
            gaia_test_tasks[1],
            gaia_test_files,
            t[1],
        )
        create_jsonl(
            f"gaia_test_level_3__{t[0]}",
            gaia_test_tasks[2],
            gaia_test_files,
            t[1],
        )


if __name__ == "__main__" and __package__ is None:
    main()
