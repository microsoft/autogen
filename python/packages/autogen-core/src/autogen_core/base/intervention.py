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


def _warn_if_none(result: Any, handler_name: str) -> Any:
    """
    Utility function to check if the intervention handler returned None and issue a warning.
    
    Args:
        result: The return value from the intervention handler
        handler_name: Name of the intervention handler method for the warning message
    
    Returns:
        The original result value
    """
    if result is None:
        warnings.warn(
            f"Intervention handler {handler_name} returned None. This might be unintentional. "
            "Consider returning the original message or DropMessage explicitly.",
            RuntimeWarning,
            stacklevel=2
        )
    return result


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
        return warn_if_none(result, "on_send")

    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any | type[DropMessage]:
        result = message
        return warn_if_none(result, "on_publish")

    async def on_response(self, message: Any, *, sender: AgentId, recipient: AgentId | None) -> Any | type[DropMessage]:
        result = message
        return warn_if_none(result, "on_response")
