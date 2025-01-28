import json
import os
import re
import sys

from huggingface_hub import snapshot_download

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

SCENARIO_DIR = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir))
TEMPLATES_DIR = os.path.join(SCENARIO_DIR, "Templates")
TASKS_DIR = os.path.join(SCENARIO_DIR, "Tasks")
DOWNLOADS_DIR = os.path.join(SCENARIO_DIR, "Downloads")
REPO_DIR = os.path.join(DOWNLOADS_DIR, "AssistantBench")


def download_assistantbench():
    """Download the AssistantBench benchmark from Hugging Face."""

    if not os.path.isdir(DOWNLOADS_DIR):
        os.mkdir(DOWNLOADS_DIR)

    """Download the AssistantBench dataset from Hugging Face Hub"""
    snapshot_download(
        repo_id="AssistantBench/AssistantBench",
        repo_type="dataset",
        local_dir=REPO_DIR,
        local_dir_use_symlinks=True,
    )


def create_jsonl(data_file_path, file_name, template):
    """Creates a JSONL scenario file with a given name, and template path."""
    tasks = []
    with open(data_file_path) as fh:
        for line in fh:
            data = json.loads(line)
            tasks.append(data)
    file_name = os.path.basename(file_name)
    if not os.path.isdir(TASKS_DIR):
        os.mkdir(TASKS_DIR)

    with open(os.path.join(TASKS_DIR, file_name), "wt") as fh:
        for task in tasks:
            if "answer" not in task or task["answer"] is None:
                task["answer"] = ""
            print(f"Converting: [{file_name}] {task['id']}")
            template_cp_list = [template]
            record = {
                "id": task["id"],
                "template": template_cp_list,
                "substitutions": {
                    "scenario.py": {
                        "__FILE_NAME__": "",
                    },
                    "expected_answer.txt": {"__EXPECTED_ANSWER__": task["answer"]},
                    "prompt.txt": {"__PROMPT__": task["task"]},
                },
                "difficulty": task["difficulty"],
                "explanation": task["explanation"],
                "metadata": task["metadata"],
                "gold_url": task["gold_url"],
                "set": task["set"],
            }
            fh.write(json.dumps(record).strip() + "\n")


###############################################################################
def main():
    ab_validation_files = os.path.join(REPO_DIR, "assistant_bench_v1.0_dev.jsonl")
    ab_test_files = os.path.join(REPO_DIR, "assistant_bench_v1.0_test.jsonl")

    if not os.path.isfile(ab_validation_files) or not os.path.isfile(ab_test_files):
        download_assistantbench()

    if not os.path.isfile(ab_validation_files) or not os.path.isfile(ab_test_files):
        sys.exit(f"Error: '{REPO_DIR}' does not appear to be a copy of the AssistantBench repository.")

    templates = {}
    for entry in os.scandir(TEMPLATES_DIR):
        if entry.is_dir():
            templates[re.sub(r"\s", "", entry.name)] = entry.path
    print(templates)
    # make a copy of the data in the Tasks directory
    for t in templates.items():
        create_jsonl(ab_validation_files, f"assistant_bench_v1.0_dev__{t[0]}.jsonl", t[1])
        create_jsonl(ab_test_files, f"assistant_bench_v1.0_test__{t[0]}.jsonl", t[1])


if __name__ == "__main__" and __package__ is None:
    main()
