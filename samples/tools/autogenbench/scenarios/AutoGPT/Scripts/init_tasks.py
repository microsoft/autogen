#
# Run this file to download the human_eval dataset, and create a corresponding testbed scenario:
# (default: ../scenarios/human_eval_two_agents_gpt4.jsonl and ./scenarios/human_eval_two_agents_gpt35.jsonl)
#

import json
import os
import sys
import glob
import base64
from huggingface_hub import snapshot_download

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

SCENARIO_DIR = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir))
TEMPLATES_DIR = os.path.join(SCENARIO_DIR, "Templates")
TASKS_DIR = os.path.join(SCENARIO_DIR, "Tasks")
CHALLENGES_DIR = os.path.join(SCENARIO_DIR, "Challenges")


def create_jsonl(name, template):
    """Creates a JSONL scenario file with a given name, and template path."""

    if not os.path.isdir(TASKS_DIR):
        os.mkdir(TASKS_DIR)

    with open(os.path.join(TASKS_DIR, name + ".jsonl"), "wt") as fh:
        data_paths = glob.glob(str(CHALLENGES_DIR + "/*/data.json"))
        for data_path in data_paths:
            print("Converting data path: ", data_path)
            workspace = os.path.dirname(data_path)
            artifacts = os.path.join(workspace, "artifacts_in")
            custom_python = os.path.join(workspace, "custom_python")

            with open(data_path, "r") as f:
                data = json.load(f)

            should_contain = data["ground"].get("should_contain", [])
            should_not_contain = data["ground"].get("should_not_contain", [])
            case_sensitive = data["ground"].get("case_sensitive", False)

            # Figure out what files we need to copy
            template_cp_list = [template]

            # Artifacts in
            if os.path.exists(artifacts):
                template_cp_list.append(
                    [
                        artifacts,
                        "coding",
                    ]
                )

            # Custom python
            if os.path.exists(custom_python):
                template_cp_list.append(
                    [
                        custom_python,
                        "custom_python",
                    ]
                )

            record = {
                "id": data["name"],
                "template": template_cp_list,
                "substitutions": {
                    "scenario.py": {
                        "__TASK__": data["task"],
                    },
                    "check.py": {
                        "__FILE_PATTERN__": data["ground"]["files"][0],
                        "__EVAL_TYPE__": data["ground"]["eval"]["type"],
                        "__CASE_SENSITIVE__": str(case_sensitive),
                    },
                    "should_contain.json.txt": {
                        "__CONTAIN__": json.dumps(should_contain),  # Double-encoded
                    },
                    "should_not_contain.json.txt": {
                        "__NO_CONTAIN__": json.dumps(should_not_contain),  # Double-encoded
                    },
                },
            }

            fh.write(json.dumps(record).strip() + "\n")


###############################################################################
def main():
    templates = {"two_agents": os.path.join(TEMPLATES_DIR, "TwoAgents")}

    # Add coding directories if needed (these are usually empty and left out of the repo)
    for template in templates.values():
        code_dir_path = os.path.join(template, "coding")
        if not os.path.isdir(code_dir_path):
            os.mkdir(code_dir_path)

    # Create the various combinations of [models] x [templates]
    for t in templates.items():
        create_jsonl(
            f"autogpt__{t[0]}",
            t[1],
        )


if __name__ == "__main__" and __package__ is None:
    main()
