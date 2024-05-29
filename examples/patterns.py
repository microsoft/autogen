import argparse
import asyncio
import logging

import openai
from agnext.agent_components.types import SystemMessage
from agnext.application_components import (
    SingleThreadedAgentRuntime,
)
from agnext.chat.agents.chat_completion_agent import ChatCompletionAgent
from agnext.chat.agents.oai_assistant import OpenAIAssistantAgent
from agnext.chat.patterns.group_chat import GroupChat, GroupChatOutput
from agnext.chat.patterns.orchestrator_chat import OrchestratorChat
from agnext.chat.types import TextMessage
from agnext.core._agent import Agent
from agnext.agent_components.model_client import OpenAI
from agnext.core.intervention import DefaultInterventionHandler, DropMessage
from typing_extensions import Any, override

logging.basicConfig(level=logging.WARNING)
logging.getLogger("agnext").setLevel(logging.DEBUG)


class ConcatOutput(GroupChatOutput):
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


class LoggingHandler(DefaultInterventionHandler):
    send_color = "\033[31m"
    response_color = "\033[34m"
    reset_color = "\033[0m"

    @override
    async def on_send(self, message: Any, *, sender: Agent | None, recipient: Agent) -> Any | type[DropMessage]:
        if sender is None:
            print(f"{self.send_color}Sending message to {recipient.name}:{self.reset_color} {message}")
        else:
            print(
                f"{self.send_color}Sending message from {sender.name} to {recipient.name}:{self.reset_color} {message}"
            )
        return message

    @override
    async def on_response(self, message: Any, *, sender: Agent, recipient: Agent | None) -> Any | type[DropMessage]:
        if recipient is None:
            print(f"{self.response_color}Received response from {sender.name}:{self.reset_color} {message}")
        else:
            print(
                f"{self.response_color}Received response from {sender.name} to {recipient.name}:{self.reset_color} {message}"
            )
        return message


async def group_chat(message: str) -> None:
    runtime = SingleThreadedAgentRuntime(before_send=LoggingHandler())

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

    chat = GroupChat(
        "Host",
        "A round-robin chat room.",
        runtime,
        [joe, cathy],
        num_rounds=5,
        output=ConcatOutput(),
    )

    response = runtime.send_message(TextMessage(content=message, source="host"), chat)

    while not response.done():
        await runtime.process_next()

    await response


async def orchestrator_oai_assistant(message: str) -> None:
    runtime = SingleThreadedAgentRuntime(before_send=LoggingHandler())

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

    planner_oai_assistant = openai.beta.assistants.create(
        model="gpt-4-turbo",
        name="Planner",
        instructions="You are a planner of complex tasks.",
    )
    planner_oai_thread = openai.beta.threads.create()
    planner = OpenAIAssistantAgent(
        name="Planner",
        description="A planner that organizes and schedules tasks.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=planner_oai_assistant.id,
        thread_id=planner_oai_thread.id,
    )

    orchestrator_oai_assistant = openai.beta.assistants.create(
        model="gpt-4-turbo",
        name="Orchestrator",
        instructions="You are an orchestrator that coordinates the team to complete a complex task.",
    )
    orchestrator_oai_thread = openai.beta.threads.create()
    orchestrator = OpenAIAssistantAgent(
        name="Orchestrator",
        description="An orchestrator that coordinates the team.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=orchestrator_oai_assistant.id,
        thread_id=orchestrator_oai_thread.id,
    )

    chat = OrchestratorChat(
        "OrchestratorChat",
        "A software development team.",
        runtime,
        orchestrator=orchestrator,
        planner=planner,
        specialists=[developer, product_manager],
    )

    response = runtime.send_message(TextMessage(content=message, source="Customer"), chat)

    while not response.done():
        await runtime.process_next()

    print((await response).content)  # type: ignore


async def orchestrator_chat_completion(message: str) -> None:
    runtime = SingleThreadedAgentRuntime(before_send=LoggingHandler())

    developer = ChatCompletionAgent(
        name="Developer",
        description="A developer that writes code.",
        runtime=runtime,
        system_messages=[SystemMessage("You are a Python developer.")],
        model_client=OpenAI(model="gpt-3.5-turbo"),
    )

    product_manager = ChatCompletionAgent(
        name="ProductManager",
        description="A product manager that plans and comes up with specs.",
        runtime=runtime,
        system_messages=[
            SystemMessage("You are a product manager good at translating customer needs into software specifications.")
        ],
        model_client=OpenAI(model="gpt-3.5-turbo"),
    )

    planner = ChatCompletionAgent(
        name="Planner",
        description="A planner that organizes and schedules tasks.",
        runtime=runtime,
        system_messages=[SystemMessage("You are a planner of complex tasks.")],
        model_client=OpenAI(model="gpt-4-turbo"),
    )

    orchestrator = ChatCompletionAgent(
        name="Orchestrator",
        description="An orchestrator that coordinates the team.",
        runtime=runtime,
        system_messages=[
            SystemMessage("You are an orchestrator that coordinates the team to complete a complex task.")
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
    )

    chat = OrchestratorChat(
        "OrchestratorChat",
        "A software development team.",
        runtime,
        orchestrator=orchestrator,
        planner=planner,
        specialists=[developer, product_manager],
    )

    response = runtime.send_message(TextMessage(content=message, source="Customer"), chat)

    while not response.done():
        await runtime.process_next()

    print((await response).content)  # type: ignore


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a pattern demo.")
    choices = {
        "group_chat": group_chat,
        "orchestrator_oai_assistant": orchestrator_oai_assistant,
        "orchestrator_chat_completion": orchestrator_chat_completion,
    }
    parser.add_argument(
        "--pattern",
        choices=list(choices.keys()),
        help="The pattern to demo.",
    )
    parser.add_argument("--message", help="The message to send.")
    args = parser.parse_args()
    asyncio.run(choices[args.pattern](args.message))
