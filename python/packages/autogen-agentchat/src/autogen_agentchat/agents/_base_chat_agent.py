from abc import ABC, abstractmethod
from typing import List, Sequence

from autogen_core.base import CancellationToken
from autogen_core.components import FunctionCall, Image
from autogen_core.components.models import FunctionExecutionResult
from pydantic import BaseModel


class BaseMessage(BaseModel):
    """A base message."""

    source: str
    """The name of the agent that sent this message."""


class TextMessage(BaseMessage):
    """A text message."""

    content: str
    """The content of the message."""


class MultiModalMessage(BaseMessage):
    """A multimodal message."""

    content: List[str | Image]
    """The content of the message."""


class ToolCallMessage(BaseMessage):
    """A message containing a list of function calls."""

    content: List[FunctionCall]
    """The list of function calls."""


class ToolCallResultMessage(BaseMessage):
    """A message containing the results of function calls."""

    content: List[FunctionExecutionResult]
    """The list of function execution results."""


class StopMessage(BaseMessage):
    """A message requesting stop of a conversation."""

    content: str
    """The content for the stop message."""


ChatMessage = TextMessage | MultiModalMessage | ToolCallMessage | ToolCallResultMessage | StopMessage
"""A message used by agents in a team."""


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
