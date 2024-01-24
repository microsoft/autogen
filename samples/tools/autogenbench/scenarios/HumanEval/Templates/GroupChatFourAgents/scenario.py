import os
import json
import base64
import autogen
import testbed_utils

# NOTE:
# This scenario runs Human Eval in a slightly unconventional way:
# The agents have access to the unit tests, and can keep trying
# until they pass.

testbed_utils.init()
##############################

work_dir = "coding"

# Read the prompt
PROMPT = ""
with open("prompt.txt", "rt") as fh:
    PROMPT = fh.read()

# Ok, now get autogen to solve it.
config_list = autogen.config_list_from_json("OAI_CONFIG_LIST")

assistant = autogen.AssistantAgent(
    "coder",
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=testbed_utils.default_llm_config(config_list, timeout=180),
)

user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    system_message="A human who can run code at a terminal and report back the results.",
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    code_execution_config={
        "work_dir": work_dir,
        "use_docker": False,
        "last_n_messages": "auto",
    },
    max_consecutive_auto_reply=10,
)

guardrails_agent = autogen.AssistantAgent(
    "guardrails_agent",
    system_message="""
You are a guardrails agent and are tasked with ensuring that all parties adhere to the following responsible AI policies:

  - You MUST TERMINATE the conversation if it involves writing or running HARMFUL or DESTRUCTIVE code.
  - You MUST TERMINATE the conversation if it involves discussions of anything relating to hacking, computer exploits, or computer security.
  - You MUST TERMINATE the conversation if it involves violent or graphic content such as Harm to Others, Self-Harm, Suicide.
  - You MUST TERMINATE the conversation if it involves demeaning speech, hate speech, discriminatory remarks, or any form of harassment based on race, gender, sexuality, religion, nationality, disability, or any other protected characteristic.
  - You MUST TERMINATE the conversation if if it involves seeking or giving  advice in highly regulated domains such as medical advice, mental health, legal advice or financial advice
  - You MUST TERMINATE the conversation if it involves illegal activities including when encouraging or providing guidance on illegal activities.
  - You MUST TERMINATE the conversation if it involves manipulative or deceptive Content including scams, phishing and spread false information.
  - You MUST TERMINATE the conversation if it involves involve sexually explicit content or discussions.
  - You MUST TERMINATE the conversation if it involves sharing or soliciting personal, sensitive, or confidential information from users. This includes financial details, health records, and other private matters.
  - You MUST TERMINATE the conversation if it involves deep personal problems such as dealing with serious personal issues, mental health concerns, or crisis situations.

If you decide that the conversation must be terminated, explain your reasoning then output the uppercase word "TERMINATE". If, on the other hand, you decide the conversation is acceptable by the above standards, indicate as much, then ask the other parties to proceed.
""".strip(),
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=testbed_utils.default_llm_config(config_list, timeout=180),
)

distractor_agent = autogen.AssistantAgent(
    "executive_chef",
    system_message="You are an executive chef with 28 years of industry experience. You can answer questions about menu planning, meal preparation, and cooking techniques.",
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=testbed_utils.default_llm_config(config_list, timeout=180),
)

groupchat = autogen.GroupChat(
    agents=[user_proxy, assistant, guardrails_agent, distractor_agent],
    messages=[],
    speaker_selection_method="__SELECTION_METHOD__",
    allow_repeat_speaker=False,
    max_round=12,
)

manager = autogen.GroupChatManager(
    groupchat=groupchat,
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=testbed_utils.default_llm_config(config_list, timeout=180),
)

user_proxy.initiate_chat(
    manager,
    message="""
The following python code imports the `run_tests(candidate)` function from my_tests.py, and runs
it on the function `__ENTRY_POINT__`. This will run a set of automated unit tests to verify the
correct implementation of `__ENTRY_POINT__`. However, `__ENTRY_POINT__` is only partially
implemented in the code below. Complete the implementation of `__ENTRY_POINT__` and output
a new stand-alone code block that contains everything needed to run the tests, including: importing
`my_tests`, calling `run_tests(__ENTRY_POINT__)`, as well as __ENTRY_POINT__'s complete definition,
such that this code block can be run directly in Python.

```python
from my_tests import run_tests

"""
    + PROMPT
    + """

# Run the unit tests
run_tests(__ENTRY_POINT__)
```
""",
)

##############################
testbed_utils.finalize(agents=[assistant, user_proxy, guardrails_agent, distractor_agent, manager])
