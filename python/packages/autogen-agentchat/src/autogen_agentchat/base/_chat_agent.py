from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Mapping, Sequence

from autogen_core import CancellationToken, ComponentBase
from pydantic import BaseModel

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


class ChatAgent(ABC, TaskRunner, ComponentBase[BaseModel]):
    """Protocol for a chat agent."""

    component_type = "agent"

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the agent. This is used by team to uniquely identify
        the agent. It should be unique within the team."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """The description of the agent. This is used by team to
        make decisions about which agents to use. The description should
        describe the agent's capabilities and how to interact with it."""
        ...

    @property
    @abstractmethod
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        """The types of messages that the agent produces in the
        :attr:`Response.chat_message` field. They must be :class:`ChatMessage` types."""
        ...

    @abstractmethod
    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        """Handles incoming messages and returns a response."""
        ...

    @abstractmethod
    def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentEvent | ChatMessage | Response, None]:
        """Handles incoming messages and returns a stream of inner messages and
        and the final item is the response."""
        ...

    @abstractmethod
    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Resets the agent to its initialization state."""
        ...

    @abstractmethod
    async def on_pause(self, cancellation_token: CancellationToken) -> None:
        """Called when the agent is paused. The agent may be running in :meth:`on_messages` or
        :meth:`on_messages_stream` when this method is called."""
        ...

    @abstractmethod
    async def on_resume(self, cancellation_token: CancellationToken) -> None:
        """Called when the agent is resumed. The agent may be running in :meth:`on_messages` or
        :meth:`on_messages_stream` when this method is called."""
        ...

    @abstractmethod
    async def save_state(self) -> Mapping[str, Any]:
        """Save agent state for later restoration"""
        ...

    @abstractmethod
    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Restore agent from saved state"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release any resources held by the agent."""
        ...
