"""This is an example demonstrates event-driven orchestration using a
group chat manager agnent.

WARNING: do not run this example in your local machine as it involves
executing arbitrary code. Use a secure environment like a docker container
or GitHub Codespaces to run this example.
"""

import argparse
import asyncio
import logging

import aiofiles
from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.agents import ChatCompletionAgent, UserProxyAgent
from agnext.chat.memory import BufferedChatMemory
from agnext.chat.patterns.group_chat_manager import GroupChatManager
from agnext.chat.types import PublishNow
from agnext.components.models import OpenAI, SystemMessage
from agnext.components.tools import FunctionTool
from agnext.core import AgentRuntime
from typing_extensions import Annotated


async def get_user_input(prompt: str) -> Annotated[str, "The user input."]:
    return await asyncio.get_event_loop().run_in_executor(None, input, prompt)


async def confirm(message: str) -> None:
    user_input = await get_user_input(f"{message} (yes/no): ")
    if user_input.lower() not in ["yes", "y"]:
        raise ValueError("Operation cancelled by system.")


async def write_file(filename: str, content: str) -> None:
    # Ask for confirmation first.
    await confirm(f"Are you sure you want to write to {filename}?")
    async with aiofiles.open(filename, "w") as file:
        await file.write(content)


async def execute_command(command: str) -> Annotated[str, "The standard output and error of the executed command."]:
    # Ask for confirmation first.
    await confirm(f"Are you sure you want to execute {command}?")
    process = await asyncio.subprocess.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return f"stdout: {stdout.decode()}\nstderr: {stderr.decode()}"


async def read_file(filename: str) -> Annotated[str, "The content of the file."]:
    # Ask for confirmation first.
    # await confirm(f"Are you sure you want to read {filename}?")
    async with aiofiles.open(filename, "r") as file:
        return await file.read()


async def remove_file(filename: str) -> None:
    # Ask for confirmation first.
    await confirm(f"Are you sure you want to remove {filename}?")
    process = await asyncio.subprocess.create_subprocess_exec("rm", filename)
    await process.wait()
    if process.returncode != 0:
        raise ValueError(f"Error occurred while removing file: {filename}")


async def list_files(directory: str) -> Annotated[str, "The list of files in the directory."]:
    # Ask for confirmation first.
    # await confirm(f"Are you sure you want to list files in {directory}?")
    process = await asyncio.subprocess.create_subprocess_exec(
        "ls",
        directory,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if stderr:
        raise ValueError(f"Error occurred while listing files: {stderr.decode()}")
    return stdout.decode()


def software_consultancy(runtime: AgentRuntime) -> UserProxyAgent:  # type: ignore
    developer = ChatCompletionAgent(
        name="Developer",
        description="A Python software developer.",
        runtime=runtime,
        system_messages=[SystemMessage("Your are a Python developer. Use your skills to write Python code.")],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=BufferedChatMemory(buffer_size=10),
        tools=[
            FunctionTool(
                write_file,
                name="write_file",
                description="Write code to a file.",
            ),
            FunctionTool(
                read_file,
                name="read_file",
                description="Read code from a file.",
            ),
            FunctionTool(list_files, name="list_files", description="List files in a directory."),
        ],
    )
    tester = ChatCompletionAgent(
        name="Tester",
        description="A Python software tester.",
        runtime=runtime,
        system_messages=[
            SystemMessage(
                "You are a Python tester. Use your skills to test code written by the developer and designer."
            )
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=BufferedChatMemory(buffer_size=10),
        tools=[
            FunctionTool(
                execute_command,
                name="execute_command",
                description="Execute a unix shell command.",
            ),
            FunctionTool(
                read_file,
                name="read_file",
                description="Read code from a file.",
            ),
            FunctionTool(list_files, name="list_files", description="List files in a directory."),
        ],
    )
    product_manager = ChatCompletionAgent(
        name="ProductManager",
        description="A product manager for a software consultancy. Interface with the customer and gather requirements for the developer.",
        runtime=runtime,
        system_messages=[
            SystemMessage(
                "You are a product manager. Interface with the customer and gather requirements for the developer and user experience designer."
            )
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=BufferedChatMemory(buffer_size=10),
        tools=[
            FunctionTool(
                read_file,
                name="read_file",
                description="Read from a file.",
            ),
            FunctionTool(list_files, name="list_files", description="List files in a directory."),
        ],
    )
    ux_designer = ChatCompletionAgent(
        name="UserExperienceDesigner",
        description="A user experience designer for creating user interfaces.",
        runtime=runtime,
        system_messages=[
            SystemMessage("You are a user experience designer. Design user interfaces for the developer.")
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=BufferedChatMemory(buffer_size=10),
        tools=[
            FunctionTool(
                write_file,
                name="write_file",
                description="Write code to a file.",
            ),
            FunctionTool(
                read_file,
                name="read_file",
                description="Read code from a file.",
            ),
            FunctionTool(list_files, name="list_files", description="List files in a directory."),
        ],
    )
    customer = UserProxyAgent(
        name="Customer",
        description="A customer requesting for help.",
        runtime=runtime,
        user_input_prompt=f"{'-'*50}\nYou:\n",
    )
    _ = GroupChatManager(
        name="GroupChatManager",
        description="A group chat manager.",
        runtime=runtime,
        memory=BufferedChatMemory(buffer_size=10),
        model_client=OpenAI(model="gpt-4-turbo"),
        participants=[developer, tester, product_manager, ux_designer, customer],
        on_message_received=lambda message: print(f"{'-'*50}\n{message.source}: {message.content}"),
    )
    return customer


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    user_proxy = software_consultancy(runtime)
    # Request the user to start the conversation.
    runtime.send_message(PublishNow(), user_proxy)
    while True:
        # TODO: Add a way to stop the loop.
        await runtime.process_next()
        await asyncio.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat with software development team.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("agnext").setLevel(logging.DEBUG)

    asyncio.run(main())
