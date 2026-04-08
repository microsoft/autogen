from typing import Any, AsyncGenerator, List, Mapping, Sequence, Union

from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient

from ..base import Handoff, Response
from ..messages import BaseAgentEvent, BaseChatMessage
from ._assistant_agent import AssistantAgent
from ._base_chat_agent import BaseChatAgent


class HandoffPlannerAgent(BaseChatAgent):
    """
    A Planner Agent that analyzes the user goal, creates a step-by-step plan,
    and automatically delegates tasks by dynamically creating a handoff tool for each worker agent.
    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        worker_agents: List[Union[BaseChatAgent, str]],
        description: str = "A planner agent that creates plans and delegates tasks.",
        **kwargs: Any
    ):
        super().__init__(name=name, description=description)

        # The Magic: Automatically create Handoff logic utilizing the patterns in `_handoff.py`
        handoffs: List[Handoff] = []
        for worker in worker_agents:
            # Flexible: accept either string names or fully instantiated agents
            target_name = worker.name if hasattr(worker, "name") else str(worker)
            handoff = Handoff(target=target_name)
            handoffs.append(handoff)

        system_message = (
            "1. Analyze the user goal. 2. Create a step-by-step plan. "
            "3. Use the provided handoff tools to delegate each step to the appropriate specialist."
        )

        # We compose with AssistantAgent so we get native stream processing, tool calling, 
        # and most importantly: native HandoffMessage emission. 
        self._assistant = AssistantAgent(
            name=name,
            model_client=model_client,
            description=description,
            system_message=system_message,
            handoffs=handoffs,
            **kwargs,
        )

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return self._assistant.produced_message_types

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        return await self._assistant.on_messages(messages, cancellation_token)

    async def on_messages_stream(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        async for msg in self._assistant.on_messages_stream(messages, cancellation_token):
            yield msg

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        await self._assistant.on_reset(cancellation_token)

    async def save_state(self) -> Mapping[str, Any]:
        return await self._assistant.save_state()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        await self._assistant.load_state(state)

    async def close(self) -> None:
        await self._assistant.close()
