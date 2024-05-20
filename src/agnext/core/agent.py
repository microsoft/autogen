from typing import Protocol, Sequence, Type, TypeVar

from agnext.core.cancellation_token import CancellationToken

T = TypeVar("T")


class Agent(Protocol[T]):
    @property
    def name(self) -> str: ...

    @property
    def subscriptions(self) -> Sequence[Type[T]]: ...

    async def on_message(self, message: T, cancellation_token: CancellationToken) -> T: ...
