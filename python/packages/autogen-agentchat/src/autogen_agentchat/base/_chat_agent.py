from typing import Protocol, Sequence, runtime_checkable

from autogen_core.base import CancellationToken

from ..messages import ChatMessage
from ._task import TaskResult, TaskRunner
from ._termination import TerminationCondition


@runtime_checkable
class ChatAgent(TaskRunner, Protocol):
    """Protocol for a chat agent."""

    @property
    def name(self) -> str:
        """The name of the agent. This is used by team to uniquely identify
        the agent. It should be unique within the team."""
        ...

    @property
    def description(self) -> str:
        """The description of the agent. This is used by team to
        make decisions about which agents to use. The description should
        describe the agent's capabilities and how to interact with it."""
        ...

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> ChatMessage:
        """Handle incoming messages and return a response message."""
        ...

    async def run(
        self,
        task: str,
        *,
        cancellation_token: CancellationToken | None = None,
        termination_condition: TerminationCondition | None = None,
    ) -> TaskResult:
        """Run the agent with the given task and return the result."""
        ...
