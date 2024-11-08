from dataclasses import dataclass
from typing import AsyncGenerator, List, Protocol, Sequence, runtime_checkable

from autogen_core.base import CancellationToken

from ..messages import ChatMessage, InnerMessage
from ._task import TaskRunner


@dataclass(kw_only=True)
class Response:
    """A response from calling :meth:`ChatAgent.on_messages`."""

    chat_message: ChatMessage
    """A chat message produced by the agent as the response."""

    inner_messages: List[InnerMessage] | None = None
    """Inner messages produced by the agent."""


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
    def produced_message_types(self) -> List[type[ChatMessage]]:
        """The types of messages that the agent produces."""
        ...

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        """Handles incoming messages and returns a response."""
        ...

    def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[InnerMessage | Response, None]:
        """Handles incoming messages and returns a stream of inner messages and
        and the final item is the response."""
        ...

    async def reset(self, cancellation_token: CancellationToken) -> None:
        """Resets the agent to its initialization state."""
        ...
