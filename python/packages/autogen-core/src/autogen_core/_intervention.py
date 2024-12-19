from typing import Any, Awaitable, Callable, Protocol, final

__all__ = [
    "DropMessage",
    "InterventionFunction",
]


@final
class DropMessage: ...


InterventionFunction = Callable[[Any], Any | Awaitable[type[DropMessage]]]
