from typing import Awaitable, Callable, Protocol, Sequence, TypeVar, final

from agnext.core.agent import Agent


@final
class DropMessage: ...


T = TypeVar("T")

InterventionFunction = Callable[[T], T | Awaitable[type[DropMessage]]]


class InterventionHandler(Protocol[T]):
    async def on_send(self, message: T, *, sender: Agent[T] | None, recipient: Agent[T]) -> T | type[DropMessage]: ...
    async def on_broadcast(self, message: T, *, sender: Agent[T] | None) -> T | type[DropMessage]: ...
    async def on_response(
        self, message: T, *, sender: Agent[T], recipient: Agent[T] | None
    ) -> T | type[DropMessage]: ...
    async def on_broadcast_response(
        self, message: Sequence[T], *, recipient: Agent[T] | None
    ) -> Sequence[T] | type[DropMessage]: ...


class DefaultInterventionHandler(InterventionHandler[T]):
    async def on_send(self, message: T, *, sender: Agent[T] | None, recipient: Agent[T]) -> T | type[DropMessage]:
        return message

    async def on_broadcast(self, message: T, *, sender: Agent[T] | None) -> T | type[DropMessage]:
        return message

    async def on_response(self, message: T, *, sender: Agent[T], recipient: Agent[T] | None) -> T | type[DropMessage]:
        return message

    async def on_broadcast_response(
        self, message: Sequence[T], *, recipient: Agent[T] | None
    ) -> Sequence[T] | type[DropMessage]:
        return message
