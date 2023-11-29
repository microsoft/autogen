import os
import json
import autogen
import testbed_utils

testbed_utils.init()
##############################

config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["__MODEL__"]},
)

assistant = autogen.AssistantAgent(
    "assistant",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    llm_config=testbed_utils.default_llm_config(config_list, timeout=180),
)
user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    max_consecutive_auto_reply=10,
    default_auto_reply="",
)

filename = "__FILE_NAME__".strip()
question = """
__PROMPT__
""".strip()

if len(filename) > 0:
    question = f"Consider the file '{filename}', which can be read from the current working directory. {question}"

user_proxy.initiate_chat(
    assistant,
    message=f"""
I will ask you a question. Report your thoughts, and finish your answer with the following template: FINAL ANSWER: [YOUR FINAL ANSWER].
YOUR FINAL ANSWER should be a number OR as few words as possible OR a comma separated list of numbers and/or strings.
If you are asked for a number, don't use comma to write your number neither use units such as $ or percent sign unless specified otherwise.
If you are asked for a string, don’t use articles, neither abbreviations (e.g. for cities), and write the digits in plain text unless specified otherwise.
If you are asked for a comma separated list, apply the above rules depending of whether the element to be put in the list is a number or a string.

Question: {question}
""".strip(),
)


##############################
testbed_utils.finalize(agents=[assistant, user_proxy])
