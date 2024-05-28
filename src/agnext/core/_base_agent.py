import warnings
from abc import ABC, abstractmethod
from asyncio import Future
from typing import Any, Mapping, Sequence, TypeVar

from agnext.core._agent_runtime import AgentRuntime
from agnext.core._cancellation_token import CancellationToken

from ._agent import Agent

ConsumesT = TypeVar("ConsumesT")
ProducesT = TypeVar("ProducesT", covariant=True)

OtherConsumesT = TypeVar("OtherConsumesT")
OtherProducesT = TypeVar("OtherProducesT")


class BaseAgent(ABC, Agent):
    def __init__(self, name: str, router: AgentRuntime) -> None:
        self._name = name
        self._router = router
        router.add_agent(self)

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def subscriptions(self) -> Sequence[type]:
        return []

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
