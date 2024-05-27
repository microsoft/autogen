import argparse
import asyncio
from typing import Any

import openai
from agnext.agent_components.model_client import OpenAI
from agnext.application_components import (
    SingleThreadedAgentRuntime,
)
from agnext.chat.agents.oai_assistant import OpenAIAssistantAgent
from agnext.chat.messages import ChatMessage
from agnext.chat.patterns.group_chat import GroupChat, Output
from agnext.chat.patterns.orchestrator import Orchestrator
from agnext.chat.types import TextMessage


class ConcatOutput(Output):
    def __init__(self) -> None:
        self._output = ""

    def on_message_received(self, message: Any) -> None:
        match message:
            case TextMessage(content=content):
                self._output += content
            case _:
                ...

    def get_output(self) -> Any:
        return self._output

    def reset(self) -> None:
        self._output = ""


async def group_chat(message: str) -> None:
    runtime = SingleThreadedAgentRuntime()

    joe_oai_assistant = openai.beta.assistants.create(
        model="gpt-3.5-turbo",
        name="Joe",
        instructions="You are a commedian named Joe. Make the audience laugh.",
    )
    joe_oai_thread = openai.beta.threads.create()
    joe = OpenAIAssistantAgent(
        name="Joe",
        description="Joe the commedian.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=joe_oai_assistant.id,
        thread_id=joe_oai_thread.id,
    )

    cathy_oai_assistant = openai.beta.assistants.create(
        model="gpt-3.5-turbo",
        name="Cathy",
        instructions="You are a poet named Cathy. Write beautiful poems.",
    )
    cathy_oai_thread = openai.beta.threads.create()
    cathy = OpenAIAssistantAgent(
        name="Cathy",
        description="Cathy the poet.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=cathy_oai_assistant.id,
        thread_id=cathy_oai_thread.id,
    )

    chat = GroupChat("Host", "A round-robin chat room.", runtime, [joe, cathy], num_rounds=5, output=ConcatOutput())

    response = runtime.send_message(ChatMessage(body=message, sender="host"), chat)

    while not response.done():
        await runtime.process_next()

    print((await response).body)  # type: ignore


async def orchestrator(message: str) -> None:
    runtime = SingleThreadedAgentRuntime()

    developer_oai_assistant = openai.beta.assistants.create(
        model="gpt-3.5-turbo",
        name="Developer",
        instructions="You are a Python developer.",
    )
    developer_oai_thread = openai.beta.threads.create()
    developer = OpenAIAssistantAgent(
        name="Developer",
        description="A developer that writes code.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=developer_oai_assistant.id,
        thread_id=developer_oai_thread.id,
    )

    product_manager_oai_assistant = openai.beta.assistants.create(
        model="gpt-3.5-turbo",
        name="ProductManager",
        instructions="You are a product manager good at translating customer needs into software specifications.",
    )
    product_manager_oai_thread = openai.beta.threads.create()
    product_manager = OpenAIAssistantAgent(
        name="ProductManager",
        description="A product manager that plans and comes up with specs.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=product_manager_oai_assistant.id,
        thread_id=product_manager_oai_thread.id,
    )

    chat = Orchestrator(
        "Manager",
        "A software development team manager.",
        runtime,
        [developer, product_manager],
        model_client=OpenAI(model="gpt-3.5-turbo"),
    )

    response = runtime.send_message(
        ChatMessage(
            body=message,
            sender="customer",
        ),
        chat,
    )

    while not response.done():
        await runtime.process_next()

    print((await response).body)  # type: ignore


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a pattern demo.")
    chocies = ["group_chat", "orchestrator"]
    parser.add_argument(
        "--pattern",
        choices=chocies,
        help="The pattern to demo.",
    )
    parser.add_argument("--message", help="The message to send.")
    args = parser.parse_args()

    if args.pattern == "group_chat":
        asyncio.run(group_chat(args.message))
    elif args.pattern == "orchestrator":
        asyncio.run(orchestrator(args.message))
    else:
        raise ValueError(f"Invalid pattern: {args.pattern}")
