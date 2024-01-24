import sys
import os
from autogen import config_list_from_json
from autogen import AssistantAgent, UserProxyAgent
import tui

msgid = None
# get the first arg
if len(sys.argv) > 1:
    msgid = int(sys.argv[1])
    if msgid < 1:
        msgid = None

if msgid is None:
    print("Please specify a valid message id")
    exit(1)

config_list = config_list_from_json("OAI_CONFIG_LIST")

# TODO: Experiment with CompressibleAgent instead of AssistantAgent
assistant = AssistantAgent(
    "tinyra", system_message=tui.ASSISTANT_SYSTEM_MESSAGE, llm_config={"config_list": config_list}
)
user = UserProxyAgent(
    "user",
    code_execution_config={"work_dir": os.path.join(tui.DATA_PATH, "work_dir")},
    human_input_mode="TERMINATE",
    is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
)

messages = tui.fetch_chat_history()
history = messages[-10 : msgid - 1]
task = messages[msgid - 1]["content"]
for msg in history:
    if msg["role"] == "user":
        user.send(msg["content"], assistant, request_reply=False, silent=False)
    else:
        assistant.send(msg["content"], user, request_reply=False, silent=False)
print("Chat history loaded with {} messages".format(len(history)))
user.initiate_chat(assistant, message=task, clear_history=False)

print("Computing final output...")
user.send(
    """Based on the above conversation, create one single response for the user.
This is the final output that will be sent to the user.
Make sure that this response is good enough to be sent to the user and professional.
""",
    assistant,
    request_reply=False,
    silent=True,
)
response = assistant.generate_reply(assistant.chat_messages[user], user)
assistant.send(response, user, request_reply=False, silent=True)

last_message = assistant.chat_messages[user][-1]["content"]

print(tui.CHATDB)
tui.insert_chat_message("assistant", last_message, msgid + 1)
