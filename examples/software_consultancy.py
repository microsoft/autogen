"""This is an example demonstrates event-driven orchestration using a
group chat manager agnent.

WARNING: do not run this example in your local machine as it involves
executing arbitrary code. Use a secure environment like a docker container
or GitHub Codespaces to run this example.
"""

import argparse
import asyncio
import base64
import logging

import aiofiles
import aiohttp
import openai
from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.agents import ChatCompletionAgent, UserProxyAgent
from agnext.chat.memory import HeadAndTailChatMemory
from agnext.chat.patterns.group_chat_manager import GroupChatManager
from agnext.chat.types import PublishNow
from agnext.components.models import OpenAI, SystemMessage
from agnext.components.tools import FunctionTool
from agnext.core import AgentRuntime
from markdownify import markdownify  # type: ignore
from tqdm import tqdm
from typing_extensions import Annotated

sep = "+----------------------------------------------------------+"


async def get_user_input(prompt: str) -> Annotated[str, "The user input."]:
    return await asyncio.get_event_loop().run_in_executor(None, input, prompt)


async def confirm(message: str) -> None:
    user_input = await get_user_input(f"{message} (yes/no): ")
    if user_input.lower() not in ["yes", "y"]:
        raise ValueError(f"Operation cancelled: reason: {user_input}")


async def write_file(filename: str, content: str) -> str:
    # Ask for confirmation first.
    await confirm(f"Are you sure you want to write to {filename}?")
    async with aiofiles.open(filename, "w") as file:
        await file.write(content)
    return f"Content written to {filename}."


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
    await confirm(f"Are you sure you want to read {filename}?")
    async with aiofiles.open(filename, "r") as file:
        return await file.read()


async def remove_file(filename: str) -> str:
    # Ask for confirmation first.
    await confirm(f"Are you sure you want to remove {filename}?")
    process = await asyncio.subprocess.create_subprocess_exec("rm", filename)
    await process.wait()
    if process.returncode != 0:
        raise ValueError(f"Error occurred while removing file: {filename}")
    return f"File removed: {filename}."


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


async def browse_web(url: str) -> Annotated[str, "The content of the web page in Markdown format."]:
    # Ask for confirmation first.
    await confirm(f"Are you sure you want to browse {url}?")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            markdown = markdownify(html)  # type: ignore
            if isinstance(markdown, str):
                return markdown
            return f"Unable to parse content from {url}."


async def create_image(
    description: Annotated[str, "Describe the image to create"],
    filename: Annotated[str, "The path to save the created image"],
) -> str:
    # Ask for confirmation first.
    await confirm(f"Are you sure you want to create an image with description: {description}?")
    # Use Dalle to generate an image from the description.
    with tqdm(desc="Generating image...", leave=False) as pbar:
        client = openai.AsyncClient()
        response = await client.images.generate(model="dall-e-2", prompt=description, response_format="b64_json")
        pbar.close()
    assert len(response.data) > 0 and response.data[0].b64_json is not None
    # Save the image to a file.
    async with aiofiles.open(filename, "wb") as file:
        image_data = base64.b64decode(response.data[0].b64_json)
        await file.write(image_data)
    return f"Image created and saved to {filename}."


def software_consultancy(runtime: AgentRuntime) -> UserProxyAgent:  # type: ignore
    developer = ChatCompletionAgent(
        name="Developer",
        description="A Python software developer.",
        runtime=runtime,
        system_messages=[
            SystemMessage(
                "Your are a Python developer. \n"
                "You can read, write, and execute code. \n"
                "You can browse files and directories. \n"
                "You can also browse the web for documentation. \n"
                "You are entering a work session with the customer, product manager, UX designer, and illustrator. \n"
                "When you are given a task, you should immediately start working on it. \n"
                "Be concise and deliver now."
            )
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=HeadAndTailChatMemory(head_size=1, tail_size=10),
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
            FunctionTool(
                execute_command,
                name="execute_command",
                description="Execute a unix shell command.",
            ),
            FunctionTool(list_files, name="list_files", description="List files in a directory."),
            FunctionTool(browse_web, name="browse_web", description="Browse a web page."),
        ],
    )
    product_manager = ChatCompletionAgent(
        name="ProductManager",
        description="A product manager. "
        "Responsible for interfacing with the customer, planning and managing the project. ",
        runtime=runtime,
        system_messages=[
            SystemMessage(
                "You are a product manager. \n"
                "You can browse files and directories. \n"
                "You are entering a work session with the customer, developer, UX designer, and illustrator. \n"
                "Keep the project on track. Don't hire any more people. \n"
                "When a milestone is reached, stop and ask for customer feedback. Make sure the customer is satisfied. \n"
                "Be VERY concise."
            )
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=HeadAndTailChatMemory(head_size=1, tail_size=10),
        tools=[
            FunctionTool(
                read_file,
                name="read_file",
                description="Read from a file.",
            ),
            FunctionTool(list_files, name="list_files", description="List files in a directory."),
            FunctionTool(browse_web, name="browse_web", description="Browse a web page."),
        ],
    )
    ux_designer = ChatCompletionAgent(
        name="UserExperienceDesigner",
        description="A user experience designer for creating user interfaces.",
        runtime=runtime,
        system_messages=[
            SystemMessage(
                "You are a user experience designer. \n"
                "You can create user interfaces from descriptions. \n"
                "You can browse files and directories. \n"
                "You are entering a work session with the customer, developer, product manager, and illustrator. \n"
                "When you are given a task, you should immediately start working on it. \n"
                "Be concise and deliver now."
            )
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=HeadAndTailChatMemory(head_size=1, tail_size=10),
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
    illustrator = ChatCompletionAgent(
        name="Illustrator",
        description="An illustrator for creating images.",
        runtime=runtime,
        system_messages=[
            SystemMessage(
                "You are an illustrator. "
                "You can create images from descriptions. "
                "You are entering a work session with the customer, developer, product manager, and UX designer. \n"
                "When you are given a task, you should immediately start working on it. \n"
                "Be concise and deliver now."
            )
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=HeadAndTailChatMemory(head_size=1, tail_size=10),
        tools=[
            FunctionTool(
                create_image,
                name="create_image",
                description="Create an image from a description.",
            ),
        ],
    )
    customer = UserProxyAgent(
        name="Customer",
        description="A customer requesting for help.",
        runtime=runtime,
        user_input_prompt=f"{sep}\nYou:\n",
    )
    _ = GroupChatManager(
        name="GroupChatManager",
        description="A group chat manager.",
        runtime=runtime,
        memory=HeadAndTailChatMemory(head_size=1, tail_size=10),
        model_client=OpenAI(model="gpt-4-turbo"),
        participants=[developer, product_manager, ux_designer, illustrator, customer],
        on_message_received=lambda message: print(f"{sep}\n{message.source}: {message.content}"),
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
    description = "Work with a software development consultancy to create your own Python application."
    art = r"""
+----------------------------------------------------------+
|  ____         __ _                                       |
| / ___|  ___  / _| |___      ____ _ _ __ ___              |
| \___ \ / _ \| |_| __\ \ /\ / / _` | '__/ _ \             |
|  ___) | (_) |  _| |_ \ V  V / (_| | | |  __/             |
| |____/ \___/|_|  \__| \_/\_/ \__,_|_|  \___|             |
|                                                          |
|   ____                      _ _                          |
|  / ___|___  _ __  ___ _   _| | |_ __ _ _ __   ___ _   _  |
| | |   / _ \| '_ \/ __| | | | | __/ _` | '_ \ / __| | | | |
| | |__| (_) | | | \__ \ |_| | | || (_| | | | | (__| |_| | |
|  \____\___/|_| |_|___/\__,_|_|\__\__,_|_| |_|\___|\__, | |
|                                                   |___/  |
|                                                          |
+----------------------------------------------------------+
| Work with a software development consultancy to create   |
| your own Python application. You can start by greeting   |
| the team!                                                |
+----------------------------------------------------------+
"""
    parser = argparse.ArgumentParser(description="Software consultancy demo.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("agnext").setLevel(logging.DEBUG)

    print(art)
    asyncio.run(main())
