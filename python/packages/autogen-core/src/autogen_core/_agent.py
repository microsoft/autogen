from typing import TYPE_CHECKING, Any, Mapping, Protocol, runtime_checkable

from ._agent_id import AgentId
from ._agent_metadata import AgentMetadata
from ._message_context import MessageContext

# Forward declaration for type checking only
if TYPE_CHECKING:
    from ._agent_runtime import AgentRuntime


@runtime_checkable
class Agent(Protocol):
    @property
    def metadata(self) -> AgentMetadata:
        """Metadata of the agent."""
        ...

    @property
    def id(self) -> AgentId:
        """ID of the agent."""
        ...

    async def bind_id_and_runtime(self, id: AgentId, runtime: "AgentRuntime") -> None:
        """Function used to bind an Agent instance to an `AgentRuntime`.

        Args:
            agent_id (AgentId): ID of the agent.
            runtime (AgentRuntime): AgentRuntime instance to bind the agent to.
        """
        ...

    async def on_message(self, message: Any, ctx: MessageContext) -> Any:
        """Message handler for the agent. This should only be called by the runtime, not by other agents.

        Args:
            message (Any): Received message. Type is one of the types in `subscriptions`.
            ctx (MessageContext): Context of the message.

        Returns:
            Any: Response to the message. Can be None.

        Raises:
            asyncio.CancelledError: If the message was cancelled.
            CantHandleException: If the agent cannot handle the message.
        """
        ...

    async def save_state(self) -> Mapping[str, Any]:
        """Save the state of the agent. The result must be JSON serializable."""
        ...

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load in the state of the agent obtained from `save_state`.

        Args:
            state (Mapping[str, Any]): State of the agent. Must be JSON serializable.
        """

        ...

    async def close(self) -> None:
        """Called when the runtime is closed"""
        ...
