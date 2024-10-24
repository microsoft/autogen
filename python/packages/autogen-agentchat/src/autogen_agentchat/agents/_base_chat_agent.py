from abc import ABC, abstractmethod
from typing import List, Sequence

from autogen_core.base import CancellationToken
from autogen_core.components.tools import Tool

from ..base import ChatAgent, TaskResult, TerminationCondition, ToolUseChatAgent
from ..messages import ChatMessage
from ..teams import RoundRobinGroupChat


class BaseChatAgent(ChatAgent, ABC):
    """Base class for a chat agent."""

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
        self,
        task: str,
        *,
        cancellation_token: CancellationToken | None = None,
        termination_condition: TerminationCondition | None = None,
    ) -> TaskResult:
        """Run the agent with the given task and return the result."""
        group_chat = RoundRobinGroupChat(participants=[self])
        result = await group_chat.run(
            task=task,
            cancellation_token=cancellation_token,
            termination_condition=termination_condition,
        )
        return result


class BaseToolUseChatAgent(BaseChatAgent, ToolUseChatAgent):
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
