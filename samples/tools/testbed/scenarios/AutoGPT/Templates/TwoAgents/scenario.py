# We would like to gracefully handle any exception
# ruff: noqa: E722

import traceback
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
import testbed_utils

# Assistant agent can call check.py to check if all the unit tests have passed
testbed_utils.init()

work_dir = "coding"

config_list = config_list_from_json("OAI_CONFIG_LIST")

assistant = AssistantAgent(
    "assistant",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    llm_config={
        "config_list": config_list,
    },
)
user_proxy = UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config={
        "work_dir": work_dir,
        "use_docker": False,
    },
    max_consecutive_auto_reply=5,
)

message = """
__TASK__
""".strip()

# Solve the task
try:
    user_proxy.initiate_chat(
        assistant,
        message=message,
    )
except:
    traceback.print_exc()

# Check the results
assistant.send(
    "```bash\npython ../check.py\n```",
    user_proxy,
    request_reply=False,
    silent=True,
)
reply = user_proxy.generate_reply(sender=assistant)
print(reply)

testbed_utils.finalize(agents=[assistant, user_proxy])
