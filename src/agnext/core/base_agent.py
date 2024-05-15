from abc import ABC, abstractmethod
from asyncio import Future
from typing import List, Sequence, Type, TypeVar

from agnext.core.message_router import MessageRouter

from .agent import Agent
from .message import Message

T = TypeVar("T", bound=Message)


class BaseAgent(ABC, Agent[T]):
    def __init__(self, name: str, router: MessageRouter[T]) -> None:
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
    async def on_event(self, event: T) -> T: ...

    def _send_message(self, message: T, destination: Agent[T]) -> Future[T]:
        return self._router.send_message(message, destination)

    def _broadcast_message(self, message: T) -> Future[List[T]]:
        return self._router.broadcast_message(message)
