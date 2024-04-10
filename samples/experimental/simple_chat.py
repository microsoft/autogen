import os
import asyncio
import aioconsole

from autogen.coding import LocalCommandLineCodeExecutor
from autogen.experimental import AssistantAgent, TwoAgentChat, UserProxyAgent, OpenAI
from autogen.experimental.drivers import run_in_terminal
from autogen.experimental.termination_managers import ReflectionTerminationManager


async def user_input(prompt: str) -> str:
    res = await aioconsole.ainput(prompt)  # type: ignore
    if not isinstance(res, str):
        raise ValueError("Expected a string")
    return res


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

    model_client = OpenAI(model="gpt-4-0125-preview", api_key=os.environ["OPENAI_API_KEY"])

    json_model_client = OpenAI(
        model="gpt-4-0125-preview", api_key=os.environ["OPENAI_API_KEY"], response_format={"type": "json_object"}
    )

    assistant = AssistantAgent(name="agent", system_message=code_writer_system_message, model_client=model_client)
    user_proxy = UserProxyAgent(
        name="user", human_input_callback=user_input, code_executor=LocalCommandLineCodeExecutor()
    )
    chat = TwoAgentChat(
        assistant,
        user_proxy,
        termination_manager=ReflectionTerminationManager(
            model_client=json_model_client, goal="The code has run and the plot was shown."
        ),
        initial_message="Plot the graph of NVDA vs AAPL ytd.",
    )
    await run_in_terminal(chat)
    print(chat.termination_result)


if __name__ == "__main__":
    asyncio.run(main())
