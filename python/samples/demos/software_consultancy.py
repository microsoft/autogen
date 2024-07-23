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
import os
import sys

import aiofiles
import aiohttp
import openai
from agnext.application import SingleThreadedAgentRuntime
from agnext.components.models import SystemMessage
from agnext.components.tools import FunctionTool
from agnext.core import AgentRuntime
from markdownify import markdownify  # type: ignore
from tqdm import tqdm
from typing_extensions import Annotated

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.agents import ChatCompletionAgent
from common.memory import HeadAndTailChatMemory
from common.patterns._group_chat_manager import GroupChatManager
from common.utils import get_chat_completion_client_from_envs
from utils import TextualChatApp, TextualUserAgent


async def write_file(filename: str, content: str) -> str:
    async with aiofiles.open(filename, "w") as file:
        await file.write(content)
    return f"Content written to {filename}."


async def execute_command(command: str) -> Annotated[str, "The standard output and error of the executed command."]:
    process = await asyncio.subprocess.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return f"stdout: {stdout.decode()}\nstderr: {stderr.decode()}"


async def read_file(filename: str) -> Annotated[str, "The content of the file."]:
    async with aiofiles.open(filename, "r") as file:
        return await file.read()


async def remove_file(filename: str) -> str:
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


async def software_consultancy(runtime: AgentRuntime, app: TextualChatApp) -> None:  # type: ignore
    user_agent = await runtime.register_and_get(
        "Customer",
        lambda: TextualUserAgent(
            description="A customer looking for help.",
            app=app,
        ),
    )
    developer = await runtime.register_and_get(
        "Developer",
        lambda: ChatCompletionAgent(
            description="A Python software developer.",
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
            model_client=get_chat_completion_client_from_envs(model="gpt-4-turbo"),
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
            tool_approver=user_agent,
        ),
    )

    product_manager = await runtime.register_and_get(
        "ProductManager",
        lambda: ChatCompletionAgent(
            description="A product manager. "
            "Responsible for interfacing with the customer, planning and managing the project. ",
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
            model_client=get_chat_completion_client_from_envs(model="gpt-4-turbo"),
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
            tool_approver=user_agent,
        ),
    )
    ux_designer = await runtime.register_and_get(
        "UserExperienceDesigner",
        lambda: ChatCompletionAgent(
            description="A user experience designer for creating user interfaces.",
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
            model_client=get_chat_completion_client_from_envs(model="gpt-4-turbo"),
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
            tool_approver=user_agent,
        ),
    )

    illustrator = await runtime.register_and_get(
        "Illustrator",
        lambda: ChatCompletionAgent(
            description="An illustrator for creating images.",
            system_messages=[
                SystemMessage(
                    "You are an illustrator. "
                    "You can create images from descriptions. "
                    "You are entering a work session with the customer, developer, product manager, and UX designer. \n"
                    "When you are given a task, you should immediately start working on it. \n"
                    "Be concise and deliver now."
                )
            ],
            model_client=get_chat_completion_client_from_envs(model="gpt-4-turbo"),
            memory=HeadAndTailChatMemory(head_size=1, tail_size=10),
            tools=[
                FunctionTool(
                    create_image,
                    name="create_image",
                    description="Create an image from a description.",
                ),
            ],
            tool_approver=user_agent,
        ),
    )
    await runtime.register(
        "GroupChatManager",
        lambda: GroupChatManager(
            description="A group chat manager.",
            memory=HeadAndTailChatMemory(head_size=1, tail_size=10),
            model_client=get_chat_completion_client_from_envs(model="gpt-4-turbo"),
            participants=[developer, product_manager, ux_designer, illustrator, user_agent],
        ),
    )
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
| Work with a software development consultancy to create   |
| your own Python application. You are working with a team |
| of the following agents:                                 |
| 1. 🤖 Developer: A Python software developer.             |
| 2. 🤖 ProductManager: A product manager.                  |
| 3. 🤖 UserExperienceDesigner: A user experience designer. |
| 4. 🤖 Illustrator: An illustrator.                        |
+----------------------------------------------------------+
"""
    app.welcoming_notice = art


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    app = TextualChatApp(runtime, user_name="You")
    await software_consultancy(runtime, app)
    # Start the runtime.
    _run_context = runtime.start()
    # Start the app.
    await app.run_async()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Software consultancy demo.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("agnext").setLevel(logging.DEBUG)
        handler = logging.FileHandler("software_consultancy.log")
        logging.getLogger("agnext").addHandler(handler)
    asyncio.run(main())
