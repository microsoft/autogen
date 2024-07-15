import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Callable

import openai
from agnext.application import (
    SingleThreadedAgentRuntime,
)
from agnext.components.models import OpenAIChatCompletionClient, SystemMessage
from agnext.components.tools import BaseTool
from agnext.core import AgentRuntime, CancellationToken
from pydantic import BaseModel, Field
from tavily import TavilyClient  # type: ignore

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from common.agents import ChatCompletionAgent, OpenAIAssistantAgent
from common.memory import BufferedChatMemory
from common.patterns._orchestrator_chat import OrchestratorChat
from common.types import TextMessage

logging.basicConfig(level=logging.WARNING)
logging.getLogger("agnext").setLevel(logging.DEBUG)


class SearchQuery(BaseModel):
    query: str = Field(description="The search query.")


class SearchResult(BaseModel):
    result: str = Field(description="The search results.")


class SearchTool(BaseTool[SearchQuery, SearchResult]):
    def __init__(self) -> None:
        super().__init__(
            args_type=SearchQuery,
            return_type=SearchResult,
            name="search",
            description="Search the web.",
        )

    async def run(self, args: SearchQuery, cancellation_token: CancellationToken) -> SearchResult:
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))  # type: ignore
        result = await asyncio.create_task(client.search(args.query))  # type: ignore
        if result:
            return SearchResult(result=json.dumps(result, indent=2, ensure_ascii=False))

        return SearchResult(result="No results found.")


def software_development(runtime: AgentRuntime) -> OrchestratorChat:  # type: ignore
    developer = runtime.register_and_get_proxy(
        "Developer",
        lambda: ChatCompletionAgent(
            description="A developer that writes code.",
            system_messages=[SystemMessage("You are a Python developer.")],
            memory=BufferedChatMemory(buffer_size=10),
            model_client=OpenAIChatCompletionClient(model="gpt-4-turbo"),
        ),
    )

    tester_oai_assistant = openai.beta.assistants.create(
        model="gpt-4-turbo",
        description="A software tester that runs test cases and reports results.",
        instructions="You are a software tester that runs test cases and reports results.",
    )
    tester_oai_thread = openai.beta.threads.create()
    tester = runtime.register_and_get_proxy(
        "Tester",
        lambda: OpenAIAssistantAgent(
            description="A software tester that runs test cases and reports results.",
            client=openai.AsyncClient(),
            assistant_id=tester_oai_assistant.id,
            thread_id=tester_oai_thread.id,
        ),
    )

    product_manager = runtime.register_and_get_proxy(
        "ProductManager",
        lambda: ChatCompletionAgent(
            description="A product manager that performs research and comes up with specs.",
            system_messages=[
                SystemMessage(
                    "You are a product manager good at translating customer needs into software specifications."
                ),
                SystemMessage("You can use the search tool to find information on the web."),
            ],
            memory=BufferedChatMemory(buffer_size=10),
            model_client=OpenAIChatCompletionClient(model="gpt-4-turbo"),
            tools=[SearchTool()],
        ),
    )

    planner = runtime.register_and_get_proxy(
        "Planner",
        lambda: ChatCompletionAgent(
            description="A planner that organizes and schedules tasks.",
            system_messages=[SystemMessage("You are a planner of complex tasks.")],
            memory=BufferedChatMemory(buffer_size=10),
            model_client=OpenAIChatCompletionClient(model="gpt-4-turbo"),
        ),
    )

    orchestrator = runtime.register_and_get_proxy(
        "Orchestrator",
        lambda: ChatCompletionAgent(
            description="An orchestrator that coordinates the team.",
            system_messages=[
                SystemMessage("You are an orchestrator that coordinates the team to complete a complex task.")
            ],
            memory=BufferedChatMemory(buffer_size=10),
            model_client=OpenAIChatCompletionClient(model="gpt-4-turbo"),
        ),
    )

    return OrchestratorChat(
        "A software development team.",
        runtime,
        orchestrator=orchestrator.id,
        planner=planner.id,
        specialists=[developer.id, product_manager.id, tester.id],
    )


async def run(message: str, user: str, scenario: Callable[[AgentRuntime], OrchestratorChat]) -> None:  # type: ignore
    runtime = SingleThreadedAgentRuntime()
    chat = scenario(runtime)
    run_context = runtime.start()
    response = await runtime.send_message(TextMessage(content=message, source=user), chat.id)
    print((await response).content)  # type: ignore
    await run_context.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a orchestrator demo.")
    choices = {"software_development": software_development}
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
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
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("agnext").setLevel(logging.DEBUG)
        handler = logging.FileHandler("inner_outter.log")
        logging.getLogger("agnext").addHandler(handler)
    asyncio.run(run(args.message, args.user, choices[args.scenario]))
