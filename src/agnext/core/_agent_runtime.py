from asyncio import Future
from typing import Any, Mapping, Protocol

from ._agent import Agent
from ._agent_id import AgentId
from ._agent_metadata import AgentMetadata
from ._cancellation_token import CancellationToken

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
        recipient: Agent | AgentId,
        *,
        sender: Agent | AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[Any]: ...

    # No responses from publishing
    def publish_message(
        self,
        message: Any,
        *,
        sender: Agent | AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[None]: ...

    def save_state(self) -> Mapping[str, Any]: ...

    def load_state(self, state: Mapping[str, Any]) -> None: ...

    def agent_metadata(self, agent: Agent | AgentId) -> AgentMetadata: ...

    def agent_save_state(self, agent: Agent | AgentId) -> Mapping[str, Any]: ...

    def agent_load_state(self, agent: Agent | AgentId, state: Mapping[str, Any]) -> None: ...
