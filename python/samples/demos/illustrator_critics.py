import argparse
import asyncio
import logging
import os
import sys

import openai
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentInstantiationContext, AgentRuntime
from autogen_core.components.models import SystemMessage

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autogen_core.base import AgentId, AgentProxy
from common.agents import ChatCompletionAgent, ImageGenerationAgent
from common.memory import BufferedChatMemory
from common.patterns._group_chat_manager import GroupChatManager
from common.utils import get_chat_completion_client_from_envs
from utils import TextualChatApp, TextualUserAgent


async def illustrator_critics(runtime: AgentRuntime, app: TextualChatApp) -> None:
    await runtime.register(
        "User",
        lambda: TextualUserAgent(
            description="A user looking for illustration.",
            app=app,
        ),
    )
    await runtime.register(
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
            model_client=get_chat_completion_client_from_envs(model="gpt-4-turbo", max_tokens=500),
        ),
    )
    descriptor = AgentProxy(AgentId("Descriptor", "default"), runtime)
    await runtime.register(
        "Illustrator",
        lambda: ImageGenerationAgent(
            description="An AI agent that generates images.",
            client=openai.AsyncOpenAI(),
            model="dall-e-3",
            memory=BufferedChatMemory(buffer_size=1),
        ),
    )
    illustrator = AgentProxy(AgentId("Illustrator", "default"), runtime)
    await runtime.register(
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
            model_client=get_chat_completion_client_from_envs(model="gpt-4-turbo"),
        ),
    )
    critic = AgentProxy(AgentId("Critic", "default"), runtime)
    await runtime.register(
        "GroupChatManager",
        lambda: GroupChatManager(
            description="A chat manager that handles group chat.",
            memory=BufferedChatMemory(buffer_size=5),
            participants=[
                AgentId("Illustrator", AgentInstantiationContext.current_agent_id().key),
                AgentId("Descriptor", AgentInstantiationContext.current_agent_id().key),
                AgentId("Critic", AgentInstantiationContext.current_agent_id().key),
            ],
            termination_word="APPROVE",
        ),
    )

    app.welcoming_notice = f"""You are now in a group chat with the following agents:

1. 🤖 {(await descriptor.metadata)['type']}: {(await descriptor.metadata).get('description')}
2. 🤖 {(await illustrator.metadata)['type']}: {(await illustrator.metadata).get('description')}
3. 🤖 {(await critic.metadata)['type']}: {(await critic.metadata).get('description')}

Provide a prompt for the illustrator to generate an image.
"""


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    app = TextualChatApp(runtime, user_name="You")
    await illustrator_critics(runtime, app)
    runtime.start()
    await app.run_async()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Illustrator-critics pattern for image generation demo.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        handler = logging.FileHandler("illustrator_critics.log")
        logging.getLogger("autogen_core").addHandler(handler)
    asyncio.run(main())
