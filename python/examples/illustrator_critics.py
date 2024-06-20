import argparse
import asyncio
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import openai
from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.agents import ChatCompletionAgent, ImageGenerationAgent
from agnext.chat.memory import BufferedChatMemory
from agnext.chat.patterns.group_chat_manager import GroupChatManager
from agnext.components.models import OpenAI, SystemMessage
from agnext.core import AgentRuntime
from utils import TextualChatApp, TextualUserAgent, start_runtime


def illustrator_critics(runtime: AgentRuntime, app: TextualChatApp) -> str:  # type: ignore
    runtime.register(
        "User",
        lambda: TextualUserAgent(
            description="A user looking for illustration.",
            app=app,
        ),
    )
    descriptor = runtime.register_and_get_proxy(
        "Descriptor",
        lambda: ChatCompletionAgent(
            description="An AI agent that provides a description of the image.",
            system_messages=[
                SystemMessage(
                    "You create short description for image. \n"
                    "In this conversation, you will be given either: \n"
                    "1. Request for new image. \n"
                    "2. Feedback on some image created. \n"
                    "In both cases, you will provide a description of a new image to be created. \n"
                    "Only provide the description of the new image and nothing else. \n"
                    "Be succinct and precise."
                ),
            ],
            memory=BufferedChatMemory(buffer_size=10),
            model_client=OpenAI(model="gpt-4-turbo", max_tokens=500),
        ),
    )
    illustrator = runtime.register_and_get_proxy(
        "Illustrator",
        lambda: ImageGenerationAgent(
            description="An AI agent that generates images.",
            client=openai.AsyncOpenAI(),
            model="dall-e-3",
            memory=BufferedChatMemory(buffer_size=1),
        ),
    )
    critic = runtime.register_and_get_proxy(
        "Critic",
        lambda: ChatCompletionAgent(
            description="An AI agent that provides feedback on images given user's requirements.",
            system_messages=[
                SystemMessage(
                    "You are an expert in image understanding. \n"
                    "In this conversation, you will judge an image given the description and provide feedback. \n"
                    "Pay attention to the details like the spelling of words and number of objects. \n"
                    "Use the following format in your response: \n"
                    "Number of each object type in the image: <Type 1 (e.g., Husky Dog)>: 1, <Type 2>: 2, ...\n"
                    "Feedback: <Your feedback here> \n"
                    "Approval: <APPROVE or REVISE> \n"
                ),
            ],
            memory=BufferedChatMemory(buffer_size=2),
            model_client=OpenAI(model="gpt-4-turbo"),
        ),
    )
    runtime.register(
        "GroupChatManager",
        lambda: GroupChatManager(
            description="A chat manager that handles group chat.",
            runtime=runtime,
            memory=BufferedChatMemory(buffer_size=5),
            participants=[illustrator.id, critic.id, descriptor.id],
            termination_word="APPROVE",
        ),
    )

    app.welcoming_notice = f"""You are now in a group chat with the following agents:

1. 🤖 {descriptor.metadata['name']}: {descriptor.metadata.get('description')}
2. 🤖 {illustrator.metadata['name']}: {illustrator.metadata.get('description')}
3. 🤖 {critic.metadata['name']}: {critic.metadata.get('description')}

Provide a prompt for the illustrator to generate an image.
"""


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    app = TextualChatApp(runtime, user_name="You")
    illustrator_critics(runtime, app)
    asyncio.create_task(start_runtime(runtime))
    await app.run_async()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Illustrator-critics pattern for image generation demo.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("agnext").setLevel(logging.DEBUG)
        handler = logging.FileHandler("illustrator_critics.log")
        logging.getLogger("agnext").addHandler(handler)
    asyncio.run(main())
