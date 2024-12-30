from dataclasses import dataclass
from typing import Any, AsyncGenerator, Mapping, Protocol, Sequence, runtime_checkable

from autogen_core import CancellationToken

from ..messages import AgentEvent, ChatMessage
from ._task import TaskRunner


@dataclass(kw_only=True)
class Response:
    """A response from calling :meth:`ChatAgent.on_messages`."""

    chat_message: ChatMessage
    """A chat message produced by the agent as the response."""

    inner_messages: Sequence[AgentEvent | ChatMessage] | None = None
    """Inner messages produced by the agent, they can be :class:`AgentEvent`
    or :class:`ChatMessage`."""


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

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        """The types of messages that the agent produces in the
        :attr:`Response.chat_message` field. They must be :class:`ChatMessage` types."""
        ...

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        """Handles incoming messages and returns a response."""
        ...

    def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentEvent | ChatMessage | Response, None]:
        """Handles incoming messages and returns a stream of inner messages and
        and the final item is the response."""
        ...

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Resets the agent to its initialization state."""
        ...

    async def save_state(self) -> Mapping[str, Any]:
        """Save agent state for later restoration"""
        ...

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Restore agent from saved state"""
        ...
