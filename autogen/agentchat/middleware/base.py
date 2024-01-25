from functools import wraps
from typing import Any, Dict, List, Optional, Protocol

__all__ = ["Middleware"]


class Middleware(Protocol):
    def call(self, *args: Any, **kwargs: Any) -> Any:
        """The function to called in the middleware chain."""
        ...  # pragma: no cover

    async def a_call(self, *args: Any, **kwargs: Any) -> Any:
        """The function to awaited in the middleware chain."""
        ...  # pragma: no cover
