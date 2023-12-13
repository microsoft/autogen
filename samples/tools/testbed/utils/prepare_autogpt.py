import base64
import glob
import json
import os
import shutil

current_file_dir = os.path.dirname(os.path.abspath(__file__))
challenge_path = os.path.join(os.path.dirname(current_file_dir), "scenarios/AutoGPT/challenges")
data_paths = glob.glob(str(challenge_path) + "/*/data.json")

for data_path in data_paths:
    print("Converting data path: ", data_path)
    workspace = os.path.dirname(data_path)

    with open(data_path, "r") as f:
        data = json.load(f)

    should_contain = data["ground"].get("should_contain", [])
    should_not_contain = data["ground"].get("should_not_contain", [])
    case_sensitive = data["ground"].get("case_sensitive", False)

    # since 'should_contain' field may contain escape characters, this can cause problems when using str() method and eval(), I used base64 encode to avoid such problems
    should_contain_base64 = []
    for word in should_contain:
        encoded_word = base64.b64encode(word.encode("utf-8")).decode("utf-8")
        should_contain_base64.append(encoded_word)

    should_not_contain_base64 = []
    for word in should_not_contain:
        encoded_word = base64.b64encode(word.encode("utf-8")).decode("utf-8")
        should_not_contain_base64.append(encoded_word)

    # copy all the files needed to 'coding' directory
    # 1. 'artifacts_in' directory: all the files needed for QA
    save_path = os.path.join(os.path.dirname(current_file_dir), "scenarios/AutoGPT")
    artifacts_in = False
    if os.path.exists(os.path.join(workspace, "artifacts_in")):
        artifacts_in = True
        target_folder = os.path.join(save_path, "Templates/TwoAgents/coding/file", data["name"])
        if os.path.exists(target_folder):
            shutil.rmtree(target_folder)
        shutil.copytree(os.path.join(workspace, "artifacts_in"), target_folder)
        # print(f"All the artifacts are copied from {os.path.join(workspace, 'artifacts_in')} to {target_folder}")

    # 2. 'custom_python' directory: all the files needed for testing python code
    if os.path.exists(os.path.join(workspace, "custom_python")):
        target_folder = os.path.join(save_path, "Templates/TwoAgents/custom_python")
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
        for filename in os.listdir(os.path.join(workspace, "custom_python")):
            shutil.copy(os.path.join(workspace, "custom_python", filename), os.path.join(target_folder, filename))
            # print(f"File copied from {os.path.join(workspace, 'custom_python', filename)} to {target_folder}")

    record = {
        "id": data["name"],
        "template": "Templates/TwoAgents",
        "substitutions": {
            "scenario.py": {
                "__MODEL__": "gpt-35-turbo-16k",
                "__TASK__": data["task"],
                "__TARGET_FOLDER__": f"file/{data['name']}" if artifacts_in else "",
            },
            "check.py": {
                "__FILE_PATTERN__": data["ground"]["files"][0],
                "__EVAL_TYPE__": data["ground"]["eval"]["type"],
                "__CASE_SENSITIVE__": str(case_sensitive),
            },
            "should_contain.txt": {
                "__CONTAIN__": str(should_contain_base64),
            },
            "should_not_contain.txt": {
                "__NO_CONTAIN__": str(should_not_contain_base64),
            },
        },
    }
    with open(os.path.join(save_path, "autogpt_twoagent_gpt35.jsonl"), "a") as f:
        f.write(json.dumps(record).strip() + "\n")

    record = {
        "id": data["name"],
        "template": "Templates/TwoAgents",
        "substitutions": {
            "scenario.py": {
                "__MODEL__": "gpt-4-1106-preview",
                "__TASK__": data["task"],
                "__TARGET_FOLDER__": f"file/{data['name']}" if artifacts_in else "",
            },
            "check.py": {
                "__FILE_PATTERN__": data["ground"]["files"][0],
                "__EVAL_TYPE__": data["ground"]["eval"]["type"],
                "__CASE_SENSITIVE__": str(case_sensitive),
            },
            "should_contain.txt": {
                "__CONTAIN__": str(should_contain_base64),
            },
            "should_not_contain.txt": {
                "__NO_CONTAIN__": str(should_not_contain_base64),
            },
        },
    }
    with open(os.path.join(save_path, "autogpt_twoagent_gpt4.jsonl"), "a") as f:
        f.write(json.dumps(record).strip() + "\n")
