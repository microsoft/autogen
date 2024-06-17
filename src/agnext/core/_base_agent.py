import warnings
from abc import ABC, abstractmethod
from asyncio import Future
from typing import Any, Mapping, Sequence, TypeVar

from ._agent import Agent
from ._agent_metadata import AgentMetadata
from ._agent_runtime import AgentRuntime
from ._cancellation_token import CancellationToken

ConsumesT = TypeVar("ConsumesT")
ProducesT = TypeVar("ProducesT", covariant=True)

OtherConsumesT = TypeVar("OtherConsumesT")
OtherProducesT = TypeVar("OtherProducesT")


class BaseAgent(ABC, Agent):
    def __init__(self, name: str, description: str, subscriptions: Sequence[type], router: AgentRuntime) -> None:
        self._name = name
        self._description = description
        self._router = router
        self._subscriptions = subscriptions
        router.add_agent(self)

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name=self._name,
            description=self._description,
            subscriptions=self._subscriptions,
        )

    @abstractmethod
    async def on_message(self, message: Any, cancellation_token: CancellationToken) -> Any: ...

    # Returns the response of the message
    def _send_message(
        self,
        message: Any,
        recipient: Agent,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[Any]:
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        future = self._router.send_message(
            message,
            sender=self,
            recipient=recipient,
            cancellation_token=cancellation_token,
        )
        cancellation_token.link_future(future)
        return future

    def _publish_message(
        self,
        message: Any,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[None]:
        if cancellation_token is None:
            cancellation_token = CancellationToken()
        future = self._router.publish_message(message, sender=self, cancellation_token=cancellation_token)
        return future

    def save_state(self) -> Mapping[str, Any]:
        warnings.warn("save_state not implemented", stacklevel=2)
        return {}

    def load_state(self, state: Mapping[str, Any]) -> None:
        warnings.warn("load_state not implemented", stacklevel=2)
        pass
