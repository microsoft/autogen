from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Mapping

from ._agent_id import AgentId
from ._agent_metadata import AgentMetadata
from ._cancellation_token import CancellationToken

if TYPE_CHECKING:
    from ._agent_runtime import AgentRuntime


class AgentProxy:
    """A helper class that allows you to use an :class:`~autogen_core.AgentId` in place of its associated :class:`~autogen_core.Agent`"""

    def __init__(self, agent: AgentId, runtime: AgentRuntime):
        self._agent = agent
        self._runtime = runtime

    @property
    def id(self) -> AgentId:
        """Target agent for this proxy"""
        return self._agent

    @property
    def metadata(self) -> Awaitable[AgentMetadata]:
        """Metadata of the agent."""
        return self._runtime.agent_metadata(self._agent)

    async def send_message(
        self,
        message: Any,
        *,
        sender: AgentId,
        cancellation_token: CancellationToken | None = None,
    ) -> Any:
        return await self._runtime.send_message(
            message,
            recipient=self._agent,
            sender=sender,
            cancellation_token=cancellation_token,
        )

    async def save_state(self) -> Mapping[str, Any]:
        """Save the state of the agent. The result must be JSON serializable."""
        return await self._runtime.agent_save_state(self._agent)

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load in the state of the agent obtained from `save_state`.

        Args:
            state (Mapping[str, Any]): State of the agent. Must be JSON serializable.
        """
        await self._runtime.agent_load_state(self._agent, state)
