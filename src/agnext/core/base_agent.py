from abc import ABC, abstractmethod
from asyncio import Future
from typing import Any, Sequence, TypeVar

from agnext.core.agent_runtime import AgentRuntime
from agnext.core.cancellation_token import CancellationToken

from .agent import Agent

ConsumesT = TypeVar("ConsumesT")
ProducesT = TypeVar("ProducesT", covariant=True)

OtherConsumesT = TypeVar("OtherConsumesT")
OtherProducesT = TypeVar("OtherProducesT")


class BaseAgent(ABC, Agent):
    def __init__(self, name: str, router: AgentRuntime) -> None:
        self._name = name
        self._router = router

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def subscriptions(self) -> Sequence[type]:
        return []

    @abstractmethod
    async def on_message(
        self, message: Any, require_response: bool, cancellation_token: CancellationToken
    ) -> Any | None: ...

    # Returns the response of the message
    def _send_message(
        self,
        message: Any,
        recipient: Agent,
        *,
        require_response: bool = True,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[Any | None]:
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        future = self._router.send_message(
            message,
            sender=self,
            recipient=recipient,
            require_response=require_response,
            cancellation_token=cancellation_token,
        )
        cancellation_token.link_future(future)
        return future

    # Returns the response of all handling agents
    def _broadcast_message(
        self,
        message: Any,
        *,
        require_response: bool = True,
        cancellation_token: CancellationToken | None = None,
    ) -> Future[Sequence[Any] | None]:
        if cancellation_token is None:
            cancellation_token = CancellationToken()
        future = self._router.broadcast_message(
            message, sender=self, require_response=require_response, cancellation_token=cancellation_token
        )
        return future
