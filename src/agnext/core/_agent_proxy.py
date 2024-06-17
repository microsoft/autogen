from asyncio import Future
from typing import Any, Mapping

from ._agent import Agent
from ._agent_id import AgentId
from ._agent_metadata import AgentMetadata
from ._agent_runtime import AgentRuntime
from ._cancellation_token import CancellationToken


class AgentProxy:
    def __init__(self, agent: Agent, runtime: AgentRuntime):
        self._agent = agent
        self._runtime = runtime

    @property
    def id(self) -> AgentId:
        """Target agent for this proxy"""
        raise NotImplementedError

    @property
    def metadata(self) -> AgentMetadata:
        """Metadata of the agent."""
        return self._runtime.agent_metadata(self._agent)

    def send_message(
        self,
        message: Any,
        *,
        sender: Agent,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[Any]:
        return self._runtime.send_message(
            message,
            recipient=self._agent,
            sender=sender,
            cancellation_token=cancellation_token,
        )

    def save_state(self) -> Mapping[str, Any]:
        """Save the state of the agent. The result must be JSON serializable."""
        return self._runtime.agent_save_state(self._agent)

    def load_state(self, state: Mapping[str, Any]) -> None:
        """Load in the state of the agent obtained from `save_state`.

        Args:
            state (Mapping[str, Any]): State of the agent. Must be JSON serializable.
        """
        self._runtime.agent_load_state(self._agent, state)
