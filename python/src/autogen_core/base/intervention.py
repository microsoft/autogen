from typing import Any, Awaitable, Callable, Protocol, final

from autogen_core.base import AgentId

__all__ = [
    "DropMessage",
    "InterventionFunction",
    "InterventionHandler",
    "DefaultInterventionHandler",
]


@final
class DropMessage: ...


InterventionFunction = Callable[[Any], Any | Awaitable[type[DropMessage]]]


class InterventionHandler(Protocol):
    async def on_send(self, message: Any, *, sender: AgentId | None, recipient: AgentId) -> Any | type[DropMessage]: ...
    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any | type[DropMessage]: ...
    async def on_response(
        self, message: Any, *, sender: AgentId, recipient: AgentId | None
    ) -> Any | type[DropMessage]: ...


class DefaultInterventionHandler(InterventionHandler):
    async def on_send(self, message: Any, *, sender: AgentId | None, recipient: AgentId) -> Any | type[DropMessage]:
        return message

    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any | type[DropMessage]:
        return message

    async def on_response(self, message: Any, *, sender: AgentId, recipient: AgentId | None) -> Any | type[DropMessage]:
        return message
