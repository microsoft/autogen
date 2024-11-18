import warnings
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


def _warn_if_none(value: Any, handler_name: str) -> None:
    """
    Utility function to check if the intervention handler returned None and issue a warning.
    
    Args:
        value: The return value to check
        handler_name: Name of the intervention handler method for the warning message
    """
    if value is None:
        warnings.warn(
            f"Intervention handler {handler_name} returned None. This might be unintentional. "
            "Consider returning the original message or DropMessage explicitly.",
            RuntimeWarning,
            stacklevel=2
        )


InterventionFunction = Callable[[Any], Any | Awaitable[type[DropMessage]]]


class InterventionHandler(Protocol):
    async def on_send(self, message: Any, *, sender: AgentId | None, recipient: AgentId) -> Any | type[DropMessage]: ...
    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any | type[DropMessage]: ...
    async def on_response(
        self, message: Any, *, sender: AgentId, recipient: AgentId | None
    ) -> Any | type[DropMessage]: ...


class DefaultInterventionHandler(InterventionHandler):
    async def on_send(self, message: Any, *, sender: AgentId | None, recipient: AgentId) -> Any | type[DropMessage]:
        result = message
        _warn_if_none(result, "on_send")
        return result

    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any | type[DropMessage]:
        result = message
        _warn_if_none(result, "on_publish")
        return result

    async def on_response(self, message: Any, *, sender: AgentId, recipient: AgentId | None) -> Any | type[DropMessage]:
        result = message
        _warn_if_none(result, "on_response")
        return result
