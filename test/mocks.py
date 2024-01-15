from contextlib import contextmanager, asynccontextmanager
from functools import wraps
from inspect import iscoroutinefunction
from unittest.mock import MagicMock, AsyncMock
from typing import Any, Callable, Generator, Optional, Union, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def monitor_calls(mock: Union[MagicMock, AsyncMock]) -> Callable[[F], F]:
    """Monitor calls to a function.

    Args:
        mock: The MagicMock object to be used to monitor calls to the function.

    Returns:
        A decorator that can be used to monitor calls to a function.

    """

    def decorator(f: F) -> F:
        @wraps(f)
        def _f_sync(*args: Any, **kwargs: Any) -> Any:
            mock(*args, **kwargs)
            return f(*args, **kwargs)

        @wraps(f)
        async def _f_async(*args: Any, **kwargs: Any) -> Any:
            await mock(*args, **kwargs)
            return await f(*args, **kwargs)

        if iscoroutinefunction(f):
            if not iscoroutinefunction(mock):
                raise TypeError(f"Cannot attach sync mock to async function: {mock=}, {f=}.")
            return _f_async
        else:
            return _f_sync

    return decorator
