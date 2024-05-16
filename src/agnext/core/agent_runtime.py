from asyncio import Future
from typing import List, Protocol, TypeVar

from agnext.core.agent import Agent

from .message import Message

T = TypeVar("T", bound=Message)

# Undeliverable - error


class AgentRuntime(Protocol[T]):
    def add_agent(self, agent: Agent[T]) -> None: ...

    # Returns the response of the message
    def send_message(self, message: T, destination: Agent[T]) -> Future[T]: ...

    # Returns the response of all handling agents
    def broadcast_message(self, message: T) -> Future[List[T]]: ...
