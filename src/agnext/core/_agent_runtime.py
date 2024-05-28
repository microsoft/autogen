from asyncio import Future
from typing import Any, Mapping, Protocol

from agnext.core._agent import Agent
from agnext.core._cancellation_token import CancellationToken

# Undeliverable - error


class AgentRuntime(Protocol):
    def add_agent(self, agent: Agent) -> None:
        """Add an agent to the runtime.

        Args:
            agent (Agent): Agent to add to the runtime.

        Note:
            The name of the agent should be unique within the runtime.
        """
        ...

    # Returns the response of the message
    def send_message(
        self,
        message: Any,
        recipient: Agent,
        *,
        sender: Agent | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[Any]: ...

    # No responses from publishing
    def publish_message(
        self,
        message: Any,
        *,
        sender: Agent | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[None]: ...

    def save_state(self) -> Mapping[str, Any]: ...

    def load_state(self, state: Mapping[str, Any]) -> None: ...
