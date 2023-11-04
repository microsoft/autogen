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

assistant = AssistantAgent(
    "assistant",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    llm_config={
        # "request_timeout": 180,  # Remove for autogen version >= 0.2, and OpenAI version >= 1.0
        "config_list": config_list,
    },
)
user_proxy = UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    max_consecutive_auto_reply=10,
    default_auto_reply="TERMINATE",
)
user_proxy.initiate_chat(assistant, message="__PROMPT__")


##############################
testbed_utils.finalize(agents=[assistant, user_proxy])
