from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Sequence

from autogen_core.base import CancellationToken

from ..base import ChatAgent, Response, TaskResult
from ..messages import AgentMessage, ChatMessage, InnerMessage, TextMessage


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

    @property
    @abstractmethod
    def produced_message_types(self) -> List[type[ChatMessage]]:
        """The types of messages that the agent produces."""
        ...

    @abstractmethod
    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        """Handles incoming messages and returns a response."""
        ...

    async def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[InnerMessage | Response, None]:
        """Handles incoming messages and returns a stream of messages and
        and the final item is the response. The base implementation in :class:`BaseChatAgent`
        simply calls :meth:`on_messages` and yields the messages in the response."""
        response = await self.on_messages(messages, cancellation_token)
        for inner_message in response.inner_messages or []:
            yield inner_message
        yield response

    async def run(
        self,
        task: str,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> TaskResult:
        """Run the agent with the given task and return the result."""
        if cancellation_token is None:
            cancellation_token = CancellationToken()
        first_message = TextMessage(content=task, source="user")
        response = await self.on_messages([first_message], cancellation_token)
        messages: List[AgentMessage] = [first_message]
        if response.inner_messages is not None:
            messages += response.inner_messages
        messages.append(response.chat_message)
        return TaskResult(messages=messages)

    async def run_stream(
        self,
        task: str,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[AgentMessage | TaskResult, None]:
        """Run the agent with the given task and return a stream of messages
        and the final task result as the last item in the stream."""
        if cancellation_token is None:
            cancellation_token = CancellationToken()
        first_message = TextMessage(content=task, source="user")
        yield first_message
        messages: List[AgentMessage] = [first_message]
        async for message in self.on_messages_stream([first_message], cancellation_token):
            if isinstance(message, Response):
                yield message.chat_message
                messages.append(message.chat_message)
                yield TaskResult(messages=messages)
            else:
                messages.append(message)
                yield message

    @abstractmethod
    async def reset(self, cancellation_token: CancellationToken) -> None:
        """Resets the agent to its initialization state."""
        ...
