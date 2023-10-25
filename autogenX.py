import os
import shutil
from pathlib import Path
import autogen
from autogen import AssistantAgent, UserProxyAgent

def clear_cache():
    # Function for cleaning up cash to
    # avoid potential spill of conversation between models
    folder_path = ".cache"
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        shutil.rmtree(folder_path)

clear_cache()
os.environ["PALM_API_KEY"] = "AIzaSyASy1MOp1ttLbwTcQ9J1SCWyLkYj_yRxoM"
config_list = autogen.config_list_from_json(env_or_file="OAI_CONFIG_LIST_X")
print(config_list)

coding_assistant = AssistantAgent(
    name="coding_assistant",
    llm_config={
        "request_timeout": 1000,
        "seed": 42,
        "config_list": config_list,
        "temperature": 0.4,
    },
)

coding_runner = UserProxyAgent(
    name="coding_runner",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: x.get("message", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"work_dir": "coding", "use_docker": False},
)
coding_runner.initiate_chat(
    coding_assistant,
    message="Calculate the percentage gain YTD for Berkshire Hathaway stock",
)

