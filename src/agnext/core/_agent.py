from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from agnext.core._cancellation_token import CancellationToken


@runtime_checkable
class Agent(Protocol):
    @property
    def name(self) -> str:
        """Name of the agent.

        Note:
            This name should be unique within the runtime.
        """
        ...

    @property
    def subscriptions(self) -> Sequence[type]:
        """Types of messages that this agent can receive."""
        ...

    async def on_message(self, message: Any, cancellation_token: CancellationToken) -> Any:
        """Message handler for the agent. This should only be called by the runtime, not by other agents.

        Args:
            message (Any): Received message. Type is one of the types in `subscriptions`.
            cancellation_token (CancellationToken): Cancellation token for the message.

        Returns:
            Any: Response to the message. Can be None.

        Notes:
            If there was a cancellation, this function should raise a `CancelledError`.
        """
        ...

    def save_state(self) -> Mapping[str, Any]:
        """Save the state of the agent. The result must be JSON serializable."""
        ...

    def load_state(self, state: Mapping[str, Any]) -> None:
        """Load in the state of the agent obtained from `save_state`.

        Args:
            state (Mapping[str, Any]): State of the agent. Must be JSON serializable.
        """

        ...
