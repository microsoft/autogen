from abc import ABC, abstractmethod
from typing import List, Sequence

from autogen_core.base import CancellationToken
from autogen_core.components.tools import Tool

from ..messages import ChatMessage
from ._base_task import TaskResult, TaskRunner


class BaseChatAgent(TaskRunner, ABC):
    """Base class for a chat agent that can participant in a team."""

    def __init__(self, name: str, description: str) -> None:
        self._name = name
        if self._name.isidentifier() is False:
            raise ValueError("The agent name must be a valid Python identifier.")
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

    async def run(
        self, task: str, *, source: str = "user", cancellation_token: CancellationToken | None = None
    ) -> TaskResult:
        # TODO: Implement this method.
        raise NotImplementedError


class BaseToolUseChatAgent(BaseChatAgent):
    """Base class for a chat agent that can use tools.

    Subclass this base class to create an agent class that uses tools by returning
    ToolCallMessage message from the :meth:`on_messages` method and receiving
    ToolCallResultMessage message from the input to the :meth:`on_messages` method.
    """

    def __init__(self, name: str, description: str, registered_tools: List[Tool]) -> None:
        super().__init__(name, description)
        self._registered_tools = registered_tools

    @property
    def registered_tools(self) -> List[Tool]:
        """The list of tools that the agent can use."""
        return self._registered_tools
