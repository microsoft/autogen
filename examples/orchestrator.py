import argparse
import asyncio
import json
import logging
import os
from typing import Annotated, Callable

import openai
from agnext.application import (
    SingleThreadedAgentRuntime,
)
from agnext.chat.agents.chat_completion_agent import ChatCompletionAgent
from agnext.chat.agents.oai_assistant import OpenAIAssistantAgent
from agnext.chat.patterns.orchestrator_chat import OrchestratorChat
from agnext.chat.types import TextMessage
from agnext.components.function_executor._impl.in_process_function_executor import (
    InProcessFunctionExecutor,
)
from agnext.components.models import OpenAI, SystemMessage
from agnext.core import Agent, AgentRuntime
from agnext.core.intervention import DefaultInterventionHandler, DropMessage
from tavily import TavilyClient
from typing_extensions import Any, override

logging.basicConfig(level=logging.WARNING)
logging.getLogger("agnext").setLevel(logging.DEBUG)


class LoggingHandler(DefaultInterventionHandler):  # type: ignore
    send_color = "\033[31m"
    response_color = "\033[34m"
    reset_color = "\033[0m"

    @override
    async def on_send(self, message: Any, *, sender: Agent | None, recipient: Agent) -> Any | type[DropMessage]:  # type: ignore
        if sender is None:
            print(f"{self.send_color}Sending message to {recipient.name}:{self.reset_color} {message}")
        else:
            print(
                f"{self.send_color}Sending message from {sender.name} to {recipient.name}:{self.reset_color} {message}"
            )
        return message

    @override
    async def on_response(self, message: Any, *, sender: Agent, recipient: Agent | None) -> Any | type[DropMessage]:  # type: ignore
        if recipient is None:
            print(f"{self.response_color}Received response from {sender.name}:{self.reset_color} {message}")
        else:
            print(
                f"{self.response_color}Received response from {sender.name} to {recipient.name}:{self.reset_color} {message}"
            )
        return message


def software_development(runtime: AgentRuntime) -> OrchestratorChat:  # type: ignore
    developer = ChatCompletionAgent(
        name="Developer",
        description="A developer that writes code.",
        runtime=runtime,
        system_messages=[SystemMessage("You are a Python developer.")],
        model_client=OpenAI(model="gpt-4-turbo"),
    )

    tester_oai_assistant = openai.beta.assistants.create(
        model="gpt-4-turbo",
        description="A software tester that runs test cases and reports results.",
        instructions="You are a software tester that runs test cases and reports results.",
    )
    tester_oai_thread = openai.beta.threads.create()
    tester = OpenAIAssistantAgent(
        name="Tester",
        description="A software tester that runs test cases and reports results.",
        runtime=runtime,
        client=openai.AsyncClient(),
        assistant_id=tester_oai_assistant.id,
        thread_id=tester_oai_thread.id,
    )

    def search(query: Annotated[str, "The search query."]) -> Annotated[str, "The search results."]:
        """Search the web."""
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        result = client.search(query)  # type: ignore
        if result:
            return json.dumps(result, indent=2, ensure_ascii=False)  # type: ignore
        return "No results found."

    function_executor = InProcessFunctionExecutor(functions=[search])

    product_manager = ChatCompletionAgent(
        name="ProductManager",
        description="A product manager that performs research and comes up with specs.",
        runtime=runtime,
        system_messages=[
            SystemMessage("You are a product manager good at translating customer needs into software specifications."),
            SystemMessage("You can use the search tool to find information on the web."),
        ],
        model_client=OpenAI(model="gpt-4-turbo"),
        function_executor=function_executor,
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

    return OrchestratorChat(
        "OrchestratorChat",
        "A software development team.",
        runtime,
        orchestrator=orchestrator,
        planner=planner,
        specialists=[developer, product_manager, tester],
    )


async def run(message: str, user: str, scenario: Callable[[AgentRuntime], OrchestratorChat]) -> None:  # type: ignore
    runtime = SingleThreadedAgentRuntime(before_send=LoggingHandler())
    chat = scenario(runtime)
    response = runtime.send_message(TextMessage(content=message, source=user), chat)
    while not response.done():
        await runtime.process_next()
    print((await response).content)  # type: ignore


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a orchestrator demo.")
    choices = {"software_development": software_development}
    parser.add_argument(
        "--scenario",
        choices=list(choices.keys()),
        help="The scenario to demo.",
        default="software_development",
    )
    parser.add_argument(
        "--user",
        default="Customer",
        help="The user to send the message. Default is 'Customer'.",
    )
    parser.add_argument("--message", help="The message to send.", required=True)
    args = parser.parse_args()
    asyncio.run(run(args.message, args.user, choices[args.scenario]))
