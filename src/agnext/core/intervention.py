from typing import Any, Awaitable, Callable, Protocol, Sequence, final

from agnext.core.agent import Agent


@final
class DropMessage: ...


InterventionFunction = Callable[[Any], Any | Awaitable[type[DropMessage]]]


class InterventionHandler(Protocol):
    async def on_send(self, message: Any, *, sender: Agent | None, recipient: Agent) -> Any | type[DropMessage]: ...
    async def on_publish(self, message: Any, *, sender: Agent | None) -> Any | type[DropMessage]: ...
    async def on_response(self, message: Any, *, sender: Agent, recipient: Agent | None) -> Any | type[DropMessage]: ...
    async def on_publish_response(
        self, message: Sequence[Any], *, recipient: Agent | None
    ) -> Sequence[Any] | type[DropMessage]: ...


class DefaultInterventionHandler(InterventionHandler):
    async def on_send(self, message: Any, *, sender: Agent | None, recipient: Agent) -> Any | type[DropMessage]:
        return message

    async def on_publish(self, message: Any, *, sender: Agent | None) -> Any | type[DropMessage]:
        return message

    async def on_response(self, message: Any, *, sender: Agent, recipient: Agent | None) -> Any | type[DropMessage]:
        return message

    async def on_publish_response(
        self, message: Sequence[Any], *, recipient: Agent | None
    ) -> Sequence[Any] | type[DropMessage]:
        return message
