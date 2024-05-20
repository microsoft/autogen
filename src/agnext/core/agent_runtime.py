from asyncio import Future
from typing import List, Protocol, TypeVar

from agnext.core.agent import Agent
from agnext.core.cancellation_token import CancellationToken

T = TypeVar("T")

# Undeliverable - error


class AgentRuntime(Protocol[T]):
    def add_agent(self, agent: Agent[T]) -> None: ...

    # Returns the response of the message
    def send_message(
        self, message: T, destination: Agent[T], cancellation_token: CancellationToken | None = None
    ) -> Future[T]: ...

    # Returns the response of all handling agents
    def broadcast_message(self, message: T, cancellation_token: CancellationToken | None = None) -> Future[List[T]]: ...
