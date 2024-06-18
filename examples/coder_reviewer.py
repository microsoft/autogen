import argparse
import asyncio
import logging
import logging.handlers
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.agents import ChatCompletionAgent
from agnext.chat.memory import BufferedChatMemory
from agnext.chat.patterns import GroupChatManager
from agnext.components.models import OpenAI, SystemMessage
from agnext.core import AgentRuntime
from utils import TextualChatApp, TextualUserAgent, start_runtime


def coder_reviewer(runtime: AgentRuntime, app: TextualChatApp) -> None:
    runtime.register(
        "Human",
        lambda: TextualUserAgent(
            description="A human user that provides a problem statement.",
            app=app,
        ),
    )
    coder = runtime.register_and_get_proxy(
        "Coder",
        lambda: ChatCompletionAgent(
            description="An agent that writes code",
            system_messages=[
                SystemMessage(
                    "You are a coder. You can write code to solve problems.\n"
                    "Work with the reviewer to improve your code."
                )
            ],
            model_client=OpenAI(model="gpt-4-turbo"),
            memory=BufferedChatMemory(buffer_size=10),
        ),
    )
    reviewer = runtime.register_and_get_proxy(
        "Reviewer",
        lambda: ChatCompletionAgent(
            description="An agent that reviews code",
            system_messages=[
                SystemMessage(
                    "You are a code reviewer. You focus on correctness, efficiency and safety of the code.\n"
                    "Respond using the following format:\n"
                    "Code Review:\n"
                    "Correctness: <Your comments>\n"
                    "Efficiency: <Your comments>\n"
                    "Safety: <Your comments>\n"
                    "Approval: <APPROVE or REVISE>\n"
                    "Suggested Changes: <Your comments>"
                )
            ],
            model_client=OpenAI(model="gpt-4-turbo"),
            memory=BufferedChatMemory(buffer_size=10),
        ),
    )
    runtime.register(
        "Manager",
        lambda: GroupChatManager(
            description="A manager that orchestrates a back-and-forth converation between a coder and a reviewer.",
            runtime=runtime,
            participants=[coder.id, reviewer.id],  # The order of the participants indicates the order of speaking.
            memory=BufferedChatMemory(buffer_size=10),
            termination_word="APPROVE",
        ),
    )
    app.welcoming_notice = f"""Welcome to the coder-reviewer demo with the following roles:
1. 🤖 {coder.metadata['name']}: {coder.metadata['description']}
2. 🧐 {reviewer.metadata['name']}: {reviewer.metadata['description']}
The coder will write code to solve a problem, and the reviewer will review the code.
The conversation will end when the reviewer approves the code.
Let's get started by providing a problem statement.
"""


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    app = TextualChatApp(runtime, user_name="You")
    coder_reviewer(runtime, app)
    asyncio.create_task(start_runtime(runtime))
    await app.run_async()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coder-reviewer pattern for code writing and review.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("agnext").setLevel(logging.DEBUG)
        handler = logging.FileHandler("coder_reviewer.log")
        logging.getLogger("agnext").addHandler(handler)
    asyncio.run(main())
