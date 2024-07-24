"""
This example demonstrates the mixture of agents implemented using pub/sub.
Mixture of agents: https://github.com/togethercomputer/moa

The example consists of two types of agents: reference agents and an aggregator agent.
The aggregator agent distributes tasks to reference agents and aggregates the results.
The reference agents handle each task independently and return the results to the aggregator agent.
"""

import asyncio
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Dict, List

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import ChatCompletionClient, SystemMessage, UserMessage
from agnext.core import CancellationToken

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.utils import get_chat_completion_client_from_envs


@dataclass
class ReferenceAgentTask:
    session_id: str
    task: str


@dataclass
class ReferenceAgentTaskResult:
    session_id: str
    result: str


@dataclass
class AggregatorTask:
    task: str


@dataclass
class AggregatorTaskResult:
    result: str


class ReferenceAgent(TypeRoutedAgent):
    """The reference agent that handles each task independently."""

    def __init__(
        self,
        description: str,
        system_messages: List[SystemMessage],
        model_client: ChatCompletionClient,
    ) -> None:
        super().__init__(description)
        self._system_messages = system_messages
        self._model_client = model_client

    @message_handler
    async def handle_task(self, message: ReferenceAgentTask, cancellation_token: CancellationToken) -> None:
        """Handle a task message. This method sends the task to the model and publishes the result."""
        task_message = UserMessage(content=message.task, source=self.metadata["name"])
        response = await self._model_client.create(self._system_messages + [task_message])
        assert isinstance(response.content, str)
        task_result = ReferenceAgentTaskResult(session_id=message.session_id, result=response.content)
        await self.publish_message(task_result)


class AggregatorAgent(TypeRoutedAgent):
    """The aggregator agent that distribute tasks to reference agents and aggregates the results."""

    def __init__(
        self,
        description: str,
        system_messages: List[SystemMessage],
        model_client: ChatCompletionClient,
        num_references: int,
    ) -> None:
        super().__init__(description)
        self._system_messages = system_messages
        self._model_client = model_client
        self._num_references = num_references
        self._session_results: Dict[str, List[ReferenceAgentTaskResult]] = {}

    @message_handler
    async def handle_task(self, message: AggregatorTask, cancellation_token: CancellationToken) -> None:
        """Handle a task message. This method publishes the task to the reference agents."""
        session_id = str(uuid.uuid4())
        ref_task = ReferenceAgentTask(session_id=session_id, task=message.task)
        await self.publish_message(ref_task)

    @message_handler
    async def handle_result(self, message: ReferenceAgentTaskResult, cancellation_token: CancellationToken) -> None:
        """Handle a task result message. Once all results are received, this method
        aggregates the results and publishes the final result."""
        self._session_results.setdefault(message.session_id, []).append(message)
        if len(self._session_results[message.session_id]) == self._num_references:
            result = "\n\n".join([r.result for r in self._session_results[message.session_id]])
            response = await self._model_client.create(
                self._system_messages + [UserMessage(content=result, source=self.metadata["name"])]
            )
            assert isinstance(response.content, str)
            task_result = AggregatorTaskResult(result=response.content)
            await self.publish_message(task_result)
            self._session_results.pop(message.session_id)
            print(f"Aggregator result: {response.content}")


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    # TODO: use different models for each agent.
    await runtime.register(
        "ReferenceAgent1",
        lambda: ReferenceAgent(
            description="Reference Agent 1",
            system_messages=[SystemMessage("You are a helpful assistant that can answer questions.")],
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini", temperature=0.1),
        ),
    )
    await runtime.register(
        "ReferenceAgent2",
        lambda: ReferenceAgent(
            description="Reference Agent 2",
            system_messages=[SystemMessage("You are a helpful assistant that can answer questions.")],
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini", temperature=0.5),
        ),
    )
    await runtime.register(
        "ReferenceAgent3",
        lambda: ReferenceAgent(
            description="Reference Agent 3",
            system_messages=[SystemMessage("You are a helpful assistant that can answer questions.")],
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini", temperature=1.0),
        ),
    )
    await runtime.register(
        "AggregatorAgent",
        lambda: AggregatorAgent(
            description="Aggregator Agent",
            system_messages=[
                SystemMessage(
                    "...synthesize these responses into a single, high-quality response... Responses from models:"
                )
            ],
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
            num_references=3,
        ),
    )
    run_context = runtime.start()
    await runtime.publish_message(AggregatorTask(task="What are something fun to do in SF?"), namespace="default")

    # Keep processing messages.
    await run_context.stop_when_idle()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
