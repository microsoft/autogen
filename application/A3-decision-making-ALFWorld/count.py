import argparse
import re
import os
import json
from glob import glob

def get_dir():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', default="logs_multiagent/")
    args = parser.parse_args()
    return args.dir


def get_success_rate(directory):
    success = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, "r") as f:
                history = json.load(f)
                if (
                    "Task success, now reply TERMINATE" in history[-3]["content"] 
                    and history[-3]['role'] == 'user'
                ):
                    success += 1
    return success
            
pattern = r'\d+\.json'
directory = get_dir()
success = get_success_rate(directory)
print("Best success task number: ", success)
print("Best success rate: ", success * 100 // 134)