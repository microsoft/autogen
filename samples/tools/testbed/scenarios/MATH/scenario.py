import os
import json
import autogen

import testbed_utils

testbed_utils.init()


PROMPT = ""
with open("prompt.txt", "rt") as fh:
    PROMPT = fh.read()

ANSWER = ""
with open("answer.txt", "rt") as fh:
    ANSWER = fh.read()


####################
config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["gpt40613"]},
)
llm_config = {
    "cache_seed": 42,
    "config_list": config_list,
    "timeout": 600,
}
code_execution_config = {
    "work_dir": "coding",
    "use_docker": False,  # set to True or image name like "python:3" to use docker
}
# ---------between "user" and "assistant"---------
assistant = autogen.AssistantAgent(name="assistant", llm_config=llm_config)
user_proxy = autogen.UserProxyAgent(
    name="user",
    human_input_mode="NEVER",
    code_execution_config=code_execution_config,
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: x.get("content", "")
    and (x.get("content", "").rstrip().endswith("TERMINATE") or x.get("content", "").rstrip().endswith("TERMINATE.")),
)

user_proxy.initiate_chat(assistant, message=PROMPT)


# --------- extract reply ---------
response_with_ans = ""
messages = assistant._oai_messages[user_proxy]
for j in range(len(messages) - 1, -1, -1):
    if (
        messages[j]["role"] == "assistant"
        and messages[j]["content"].strip() != "TERMINATE"
        and messages[j]["content"].strip() != "TERMINATE."
    ):
        response_with_ans = messages[j]["content"]
        break


# ---------between "answer_checker" and "checker_proxy"---------
# define answer checker chat

check_sys_msg = """You are a helpful AI assistant. You will use your coding and language skills to verify the answer.
You are given:
    1. A problem.
    2. A reply with the answer to the problem.
    3. A ground truth answer.
Please do the following:
1. Extract the answer in the reply: "The answer is <answer extracted>".
2. Check whether the answer in the reply matches the ground truth answer. When comparison is not obvious (for example, 3*\\sqrt(6) and 7.348), you may write code to check the answer and wait for the user to execute the code.
3. After everything is done, please choose a reply from the following options:
    - "The answer is correct."
    - "The answer is approximated but should be correct. Correct Answer: <ground truth answer> | Answer extracted: <answer extracted>."
    - "The answer is incorrect. Correct Answer: <ground truth answer> | Answer extracted: <answer extracted>."
    - "The reply doesn't contain an answer." """

answer_checker = autogen.AssistantAgent(name="checker", llm_config=llm_config, system_message=check_sys_msg)
checker_proxy = autogen.UserProxyAgent(
    name="checker_proxy",
    human_input_mode="NEVER",
    code_execution_config=code_execution_config,
    max_consecutive_auto_reply=5,
    is_termination_msg=lambda x: x.get("content", "").lower()
    and (
        "the answer is correct" in x.get("content", "").lower()
        or "the answer is incorrect" in x.get("content", "").lower()
        or "the reply doesn't contain an answer" in x.get("content", "").lower()
        or "the answer is approximated but should be correct" in x.get("content", "").lower()
    ),
)

message_to_check = "Problem: " + PROMPT + f"\n\nReply: {response_with_ans}\n\nGround truth answer: " + ANSWER
checker_proxy.initiate_chat(answer_checker, message=message_to_check)


####################
testbed_utils.finalize(agents=[assistant, user_proxy, answer_checker, checker_proxy])
