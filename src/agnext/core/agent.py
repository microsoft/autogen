from typing import Protocol, Sequence, Type, TypeVar

from .message import Message

T = TypeVar("T", bound=Message)


class Agent(Protocol[T]):
    @property
    def name(self) -> str: ...

    @property
    def subscriptions(self) -> Sequence[Type[T]]: ...

    async def on_event(self, event: T) -> T: ...
