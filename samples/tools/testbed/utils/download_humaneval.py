#
# Run this file to download the human_eval dataset, and create a corresponding testbed scenario:
# (default: ../scenarios/human_eval_two_agents_gpt4.jsonl and ./scenarios/human_eval_two_agents_gpt35.jsonl)
#

import requests
import gzip
import io
import json
import os
import base64


script_path = os.path.realpath(__file__)
script_name = os.path.basename(script_path)
script_dir = os.path.dirname(script_path)

# Directory where scenarios are stored
scenarios_dir = os.path.realpath(os.path.join(script_dir, os.path.pardir, "scenarios"))
print("Saving HumanEval scenarios to: " + scenarios_dir)


# URL of the file to download
url = "https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl.gz"

# Send a HTTP request to the URL of the file
response = requests.get(url)

# Ensure we raise an error if the download failed
response.raise_for_status()

# Create a BytesIO object from the response content
buffer = io.BytesIO(response.content)

# Create a scenario file
fh_gpt4 = open(os.path.join(scenarios_dir, "human_eval_two_agents_gpt4.jsonl"), "wt")
fh_gpt35 = open(os.path.join(scenarios_dir, "human_eval_two_agents_gpt35.jsonl"), "wt")

# Open the buffer as a .gz file and read it line by line
with gzip.GzipFile(fileobj=buffer) as f_in:
    for line in f_in:
        # Parse each line as JSON
        data = json.loads(line)
        print("Converting: " + data["task_id"])

        # Write the GPT-4 scenario
        # Prompts and tests are saved in base 64 to greatly simplify escaping them as they
        # move through the various formats and scripts. I welcome a better, more readable, alternative.
        record = {
            "id": data["task_id"].replace("/", "_"),
            "template": "human_eval_two_agents.py",
            "values": {
                "__MODEL__": "gpt-4",
                "__PROMPT_BASE64__": base64.b64encode(data["prompt"].encode("utf-8")).decode("utf-8"),
                "__ENTRY_POINT__": data["entry_point"],
                "__TEST_BASE64__": base64.b64encode(data["test"].encode("utf-8")).decode("utf-8"),
            },
        }
        fh_gpt4.write(json.dumps(record).strip() + "\n")

        # Write the GPT 3.5 Version
        record["values"]["__MODEL__"] = "gpt-3.5-turbo-16k"
        fh_gpt35.write(json.dumps(record).strip() + "\n")


fh_gpt4.close()
fh_gpt35.close()
