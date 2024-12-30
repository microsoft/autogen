from typing import Any, Protocol, final

from ._agent_id import AgentId

__all__ = [
    "DropMessage",
    "InterventionHandler",
    "DefaultInterventionHandler",
]


@final
class DropMessage: ...


class InterventionHandler(Protocol):
    """An intervention handler is a class that can be used to modify, log or drop messages that are being processed by the :class:`autogen_core.base.AgentRuntime`.

    Note: Returning None from any of the intervention handler methods will result in a warning being issued and treated as "no change". If you intend to drop a message, you should return :class:`DropMessage` explicitly.
    """

    async def on_send(self, message: Any, *, sender: AgentId | None, recipient: AgentId) -> Any | type[DropMessage]: ...
    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any | type[DropMessage]: ...
    async def on_response(
        self, message: Any, *, sender: AgentId, recipient: AgentId | None
    ) -> Any | type[DropMessage]: ...


class DefaultInterventionHandler(InterventionHandler):
    """Simple class that provides a default implementation for all intervention
    handler methods, that simply returns the message unchanged. Allows for easy
    subclassing to override only the desired methods."""

    async def on_send(self, message: Any, *, sender: AgentId | None, recipient: AgentId) -> Any | type[DropMessage]:
        return message

    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any | type[DropMessage]:
        return message

    async def on_response(self, message: Any, *, sender: AgentId, recipient: AgentId | None) -> Any | type[DropMessage]:
        return message
