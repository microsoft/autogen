from io import StringIO
import autogen
from group_chat import test_group_chat
from two_agent_chat import test_two_agent_chat
import os
import sys

# default sys.stdin to "exit"
sys.stdin = StringIO("exit")

# get current file path

cwd = os.path.dirname(__file__)
tasks = os.path.join(cwd, "tasks.txt")
oai_config_json = os.path.join(cwd, "OAI_CONFIG_LIST.json")

# load tasks from tasks.txt
with open(tasks, "r") as f:
    tasks = f.readlines()
tasks = [task.strip() for task in tasks]


available_models = ['chat', 'gpt-4']
available_mode = ['roleplay', 'naive']

output = os.path.join(cwd, "output")
if not os.path.exists(output):
    os.makedirs(output)

for model in available_models:
    config_list = autogen.config_list_from_json(
        oai_config_json,
        filter_dict={"model": model}
    )

    llm_config = {
        "temperature": 0,
        "config_list": config_list,
        "request_timeout": 360,
    }

    # run group chat
    for mode in available_mode:
        test_group_chat(model, mode, llm_config, output, tasks)
        
    # run two agent chat
    test_two_agent_chat(model, llm_config, output, tasks)

    
    
    