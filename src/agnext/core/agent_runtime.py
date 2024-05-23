from asyncio import Future
from typing import Any, Protocol, Sequence

from agnext.core.agent import Agent
from agnext.core.cancellation_token import CancellationToken

# Undeliverable - error


class AgentRuntime(Protocol):
    def add_agent(self, agent: Agent) -> None: ...

    # Returns the response of the message
    def send_message(
        self,
        message: Any,
        recipient: Agent,
        *,
        require_response: bool = True,
        sender: Agent | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[Any | None]: ...

    # Returns the response of all handling agents
    def broadcast_message(
        self,
        message: Any,
        *,
        require_response: bool = True,
        sender: Agent | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[Sequence[Any] | None]: ...
