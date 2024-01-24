import sys
import os
from autogen import config_list_from_json
from autogen import AssistantAgent, UserProxyAgent, Agent
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


def terminate_on_consecutive_empty(recipient, messages, sender, **kwargs):
    # check the contents of the last N messages
    # if all empty, terminate
    all_empty = True
    last_n = 2
    for message in reversed(messages):
        if last_n == 0:
            break
        if message["role"] == "user":
            last_n -= 1
            if len(message["content"]) > 0:
                all_empty = False
                break
    if all_empty:
        return True, "TERMINATE"
    return False, None


# TODO: Experiment with CompressibleAgent instead of AssistantAgent
assistant = AssistantAgent(
    "tinyra", system_message=tui.ASSISTANT_SYSTEM_MESSAGE, llm_config={"config_list": config_list}
)

assistant.register_reply(Agent, terminate_on_consecutive_empty, 1)

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
    f"""Based on the results in above conversation, create a response for the user.
While computing the response, remember that this conversation was your inner mono-logue. The user does not need to know every detail of the conversation.
All they want to see is the appropriate result for their task (repeated below) in a manner that would be most useful.
The task was: {task}

There is no need to use the word TERMINATE in this response.
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
