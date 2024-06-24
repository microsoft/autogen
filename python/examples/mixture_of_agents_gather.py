"""This example demonstrates the mixture of agents implemented using direct
messaging and async gathering of results.
Mixture of agents: https://github.com/togethercomputer/moa"""

import asyncio
from dataclasses import dataclass
from typing import List

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import ChatCompletionClient, OpenAI, SystemMessage, UserMessage
from agnext.core import AgentId, CancellationToken


@dataclass
class ReferenceAgentTask:
    task: str


@dataclass
class ReferenceAgentTaskResult:
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
    async def handle_task(
        self, message: ReferenceAgentTask, cancellation_token: CancellationToken
    ) -> ReferenceAgentTaskResult:
        """Handle a task message. This method sends the task to the model and respond with the result."""
        task_message = UserMessage(content=message.task, source=self.metadata["name"])
        response = await self._model_client.create(self._system_messages + [task_message])
        assert isinstance(response.content, str)
        return ReferenceAgentTaskResult(result=response.content)


class AggregatorAgent(TypeRoutedAgent):
    """The aggregator agent that distribute tasks to reference agents and aggregates the results."""

    def __init__(
        self,
        description: str,
        system_messages: List[SystemMessage],
        model_client: ChatCompletionClient,
        references: List[AgentId],
    ) -> None:
        super().__init__(description)
        self._system_messages = system_messages
        self._model_client = model_client
        self._references = references

    @message_handler
    async def handle_task(self, message: AggregatorTask, cancellation_token: CancellationToken) -> AggregatorTaskResult:
        """Handle a task message. This method sends the task to the reference agents
        and aggregates the results."""
        ref_task = ReferenceAgentTask(task=message.task)
        results: List[ReferenceAgentTaskResult] = await asyncio.gather(
            *[self.send_message(ref_task, ref) for ref in self._references]
        )
        combined_result = "\n\n".join([r.result for r in results])
        response = await self._model_client.create(
            self._system_messages + [UserMessage(content=combined_result, source=self.metadata["name"])]
        )
        assert isinstance(response.content, str)
        return AggregatorTaskResult(result=response.content)


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    ref1 = runtime.register_and_get(
        "ReferenceAgent1",
        lambda: ReferenceAgent(
            description="Reference Agent 1",
            system_messages=[SystemMessage("You are a helpful assistant that can answer questions.")],
            model_client=OpenAI(model="gpt-3.5-turbo", temperature=0.1),
        ),
    )
    ref2 = runtime.register_and_get(
        "ReferenceAgent2",
        lambda: ReferenceAgent(
            description="Reference Agent 2",
            system_messages=[SystemMessage("You are a helpful assistant that can answer questions.")],
            model_client=OpenAI(model="gpt-3.5-turbo", temperature=0.5),
        ),
    )
    ref3 = runtime.register_and_get(
        "ReferenceAgent3",
        lambda: ReferenceAgent(
            description="Reference Agent 3",
            system_messages=[SystemMessage("You are a helpful assistant that can answer questions.")],
            model_client=OpenAI(model="gpt-3.5-turbo", temperature=1.0),
        ),
    )
    agg = runtime.register_and_get(
        "AggregatorAgent",
        lambda: AggregatorAgent(
            description="Aggregator Agent",
            system_messages=[
                SystemMessage(
                    "...synthesize these responses into a single, high-quality response... Responses from models:"
                )
            ],
            model_client=OpenAI(model="gpt-3.5-turbo"),
            references=[ref1, ref2, ref3],
        ),
    )
    result = runtime.send_message(AggregatorTask(task="What are something fun to do in SF?"), agg)
    while result.done() is False:
        await runtime.process_next()
    print(result.result())


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
