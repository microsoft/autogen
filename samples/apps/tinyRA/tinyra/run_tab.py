import sys
from autogen import config_list_from_json
from autogen import AssistantAgent, UserProxyAgent
import tui

msgid = None
# get the first arg
if len(sys.argv) > 1:
    msgid = int(sys.argv[1])


config_list = config_list_from_json("OAI_CONFIG_LIST")

assistant = AssistantAgent("tinyra", llm_config={"config_list": config_list})
user = UserProxyAgent(
    "user",
    code_execution_config={
        "work_dir": "agent_work_dir",
    },
    human_input_mode="TERMINATE",
    is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
)

messages = tui.fetch_chat_history()

task = messages[msgid - 1]

user.initiate_chat(assistant, message=task)

last_message = assistant.chat_messages[user][-1]["content"]

print(tui.CHATDB)
tui.insert_chat_message("assistant", last_message, msgid + 1)
