from abc import ABC, abstractmethod
from asyncio import Future
from typing import List, Sequence, Type, TypeVar

from agnext.core.agent_runtime import AgentRuntime
from agnext.core.cancellation_token import CancellationToken

from .agent import Agent

T = TypeVar("T")


class BaseAgent(ABC, Agent[T]):
    def __init__(self, name: str, router: AgentRuntime[T]) -> None:
        self._name = name
        self._router = router

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def subscriptions(self) -> Sequence[Type[T]]:
        return []

    @abstractmethod
    async def on_message(self, message: T, cancellation_token: CancellationToken) -> T: ...

    def _send_message(
        self, message: T, recipient: Agent[T], cancellation_token: CancellationToken | None = None
    ) -> Future[T]:
        if cancellation_token is None:
            cancellation_token = CancellationToken()
        future = self._router.send_message(
            message, sender=self, recipient=recipient, cancellation_token=cancellation_token
        )
        cancellation_token.link_future(future)
        return future

    def _broadcast_message(self, message: T, cancellation_token: CancellationToken | None = None) -> Future[List[T]]:
        if cancellation_token is None:
            cancellation_token = CancellationToken()
        future = self._router.broadcast_message(message, sender=self, cancellation_token=cancellation_token)
        cancellation_token.link_future(future)
        return future
