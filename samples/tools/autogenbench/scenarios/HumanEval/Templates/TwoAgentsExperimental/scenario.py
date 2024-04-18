import asyncio
import os

import aioconsole

from autogen import config_list_from_json
from autogen.coding import LocalCommandLineCodeExecutor
from autogen.experimental import AssistantAgent, OpenAI, TwoAgentChat, UserProxyAgent, AzureOpenAI
from autogen.experimental.drivers import run_in_terminal
from autogen.experimental.terminations import DefaultTermination
from autogen.experimental.types import UserMessage

# Read the prompt
PROMPT = ""
with open("prompt.txt", "rt") as fh:
    PROMPT = fh.read()

async def main() -> None:
    code_writer_system_message = """
You have been given coding capability to solve tasks using Python code.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user. Add into your code a print that confirms actions completed successfully.

If it looks like the task is done and the code has already been executed you can respond with 'TERMINATE' to end the conversation.
"""


    model_config = config_list_from_json(env_or_file="OAI_CONFIG_LIST")[0] # Just take the first for now

    if True: #model_config.get("api_type") == "azure":
        model_client = AzureOpenAI(
            model=model_config.get("model"),
            azure_endpoint=model_config.get("base_url"),
            api_key=model_config.get("api_key"),
            api_version=model_config.get("api_version"),
            model_capabilities={
                "function_calling": True,
                "json_output": True,
                "vision": False
            }
        )
    #else:
    #    model_client = OpenAI(model=model_config.get("model"), api_key=model_config.get("api_key"))

    assistant = AssistantAgent(name="agent", system_message=code_writer_system_message, model_client=model_client)

    user_proxy = UserProxyAgent(
        name="user", human_input_callback=None, code_executor=LocalCommandLineCodeExecutor(work_dir="coding")
    )
    chat = TwoAgentChat(
        assistant,
        user_proxy,
        termination_manager=DefaultTermination(),
    )
    
    message = UserMessage("""The following python code imports the `run_tests(candidate)` function from my_tests.py, and runs
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
""")

    chat.append_message(message)
    await run_in_terminal(chat)
    print(chat.termination_result)


if __name__ == "__main__":
    asyncio.run(main())
