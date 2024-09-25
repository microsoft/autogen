from abc import ABC, abstractmethod
from typing import Sequence

from autogen_core.base import CancellationToken
from autogen_core.components.models import AssistantMessage, UserMessage
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """A chat message from a user or agent."""

    content: UserMessage | AssistantMessage
    """The content of the message."""

    request_pause: bool
    """A flag indicating whether the current conversation session should be
    paused after processing this message."""


class BaseChatAgent(ABC):
    """Base class for a chat agent that can participant in a team."""

    def __init__(self, name: str, description: str) -> None:
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        """The name of the agent. This is used by team to uniquely identify
        the agent. It should be unique within the team."""
        return self._name

    @property
    def description(self) -> str:
        """The description of the agent. This is used by team to
        make decisions about which agents to use. The description should
        describe the agent's capabilities and how to interact with it."""
        return self._description

    @abstractmethod
    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> ChatMessage:
        """Handle incoming messages and return a response message."""
        ...
