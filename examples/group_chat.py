"""This is an example demonstrates event-driven orchestration using a
group chat manager agnent."""

import argparse
import asyncio
import logging

from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.agents import ChatCompletionAgent, UserProxyAgent
from agnext.chat.memory import BufferedChatMemory
from agnext.chat.patterns.group_chat_manager import GroupChatManager
from agnext.chat.types import PublishNow
from agnext.components.models import OpenAI, SystemMessage
from agnext.core import AgentRuntime


def software_development(runtime: AgentRuntime) -> UserProxyAgent:  # type: ignore
    alice = ChatCompletionAgent(
        name="Alice",
        description="A software engineer likes to code.",
        runtime=runtime,
        system_messages=[SystemMessage("Your name is Alice and you are a software engineer likes to code.")],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=BufferedChatMemory(buffer_size=10),
    )
    bob = ChatCompletionAgent(
        name="Bob",
        description="A data scientist likes to analyze data.",
        runtime=runtime,
        system_messages=[SystemMessage("Your name is Bob and you are a data scientist likes to analyze data.")],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=BufferedChatMemory(buffer_size=10),
    )
    charlie = ChatCompletionAgent(
        name="Charlie",
        description="A designer likes to design user interfaces.",
        runtime=runtime,
        system_messages=[SystemMessage("Your name is Charlie and you are a designer likes to design user interfaces.")],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=BufferedChatMemory(buffer_size=10),
    )
    susan = ChatCompletionAgent(
        name="Susan",
        description="A product manager likes to understand user's requirement and bring it into software specifications.",
        runtime=runtime,
        system_messages=[
            SystemMessage(
                "Your name is Susan and you are a product manager likes to understand user's requirement and bring it into software specifications."
            )
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        memory=BufferedChatMemory(buffer_size=10),
    )
    user_proxy = UserProxyAgent(
        name="User", description="A user requesting for help.", runtime=runtime, user_input_prompt=f"{'-'*50}\nYou:\n"
    )
    _ = GroupChatManager(
        name="GroupChatManager",
        description="A group chat manager.",
        runtime=runtime,
        memory=BufferedChatMemory(buffer_size=10),
        model_client=OpenAI(model="gpt-4-turbo"),
        participants=[alice, bob, charlie, susan, user_proxy],
        on_message_received=lambda message: print(f"{'-'*50}\n{message.source}: {message.content}"),
    )
    return user_proxy


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    user_proxy = software_development(runtime)
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
