from typing import Any, Awaitable, Callable, final

from autogen_core._message_context import MessageContext

__all__ = [
    "DropMessage",
    "InterventionFunction",
]


@final
class DropMessage: ...


InterventionFunction = Callable[
    [Any, MessageContext], Any | Awaitable[Any] | type[DropMessage] | Awaitable[type[DropMessage]]
]
