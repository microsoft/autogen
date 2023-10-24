from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
import os
import json
import testbed_utils

testbed_utils.init()
##############################

config_list = config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["__MODEL__"]},
)

assistant = AssistantAgent("assistant", llm_config={"request_timeout": 180, "config_list": config_list})
user_proxy = UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    max_consecutive_auto_reply=10,
)
user_proxy.initiate_chat(assistant, message="__PROMPT__")


##############################
testbed_utils.finalize(assistant, user_proxy)
