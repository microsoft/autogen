import asyncio
import functools
import inspect
from functools import wraps
import threading
from typing import Any, Callable, List, Optional, Protocol

from typing_extensions import TypeVar

__all__ = ["Hookable", "hookable"]

F = TypeVar("F", bound=Callable[..., Any])
H = TypeVar("H", bound=Callable[..., Any])
T = TypeVar("T")


class Middleware(Protocol):
    def call(self, *args: Any, **kwargs: Any) -> Any:
        ...  # pragma: no cover


class Hookable(Protocol):
    """Protocol for hookable functions and methods."""

    @property
    def _origin(self) -> Callable[..., Any]:
        ...  # pragma: no cover

    @property
    def _chained_call(self) -> Callable[..., Any]:
        ...  # pragma: no cover

    @property
    def _is_async(self) -> bool:
        ...  # pragma: no cover

    @property
    def _is_method(self) -> bool:
        ...  # pragma: no cover

    @property
    def _middlewares(self) -> List[Middleware]:
        ...  # pragma: no cover

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...  # pragma: no cover


def hookable(f: F) -> Hookable:
    """Decorator to make a function hookable.

    You can attach middlewares to a hookable function using the `add_middleware` or `set_middlewares` methods.

    Args:
        f: The function to make hookable.

    Returns:
        A hookable version of the function.
    """

    @wraps(f)
    def h_sync(*args: Any, **kwargs: Any) -> Any:
        return h_sync._chained_call(*args, **kwargs)  # type: ignore[attr-defined]

    @wraps(f)
    async def h_async(*args: Any, **kwargs: Any) -> Any:
        return await h_async._chained_call(*args, **kwargs)  # type: ignore[attr-defined]

    # this is to reduce number of mypy errors below, although we don't care about errors here
    h: Hookable = h_async if inspect.iscoroutinefunction(f) else h_sync  # type: ignore[assignment]

    h._origin = f  # type: ignore[misc]
    h._chained_call = f  # type: ignore[misc]

    # if the name of the first argument is `self` or `cls`, then we assume
    # this is a method, otherwise it is a function
    sig = inspect.signature(f)
    first_param_name = list(sig.parameters.keys())[0]
    h._is_method = first_param_name in ("self", "cls")  # type: ignore[misc]

    # if async, then we need to await the result
    h._is_async = inspect.iscoroutinefunction(f)  # type: ignore[misc]

    h._middlewares = []  # type: ignore[misc]

    return h


def match_caller_type(*, callee: Callable[..., Any], caller: Callable[..., Any]) -> Callable[..., Any]:
    """Match the caller type of two functions.

    If both `callee` and `caller` are both async or both sync functions, then `callee` is returned.
    If `callee` is sync and `caller` is async, then a wrapper is returned that calls `callee` and awaits the result.
    If `callee` is async and `caller` is sync, a wrapper is returned that waits for `callee` and returns the result.

    Args:
        callee: The source function.
        caller: The destination function.

    Returns:
        A function that matches the caller type of `caller`.

    Raises:
        TypeError: If `callee` is async and `caller` is sync.
    """
    # return the callee if already the same type
    if inspect.iscoroutinefunction(caller) == inspect.iscoroutinefunction(callee):
        return callee

    loop = asyncio.get_running_loop()

    if inspect.iscoroutinefunction(callee):

        @wraps(callee)
        def _sync_callee(*args: Any, **kwargs: Any) -> Any:
            coro = callee(*args, **kwargs)
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(
                timeout=2
            )  # This will block until the coroutine has completed or the timeout is reached

        return _sync_callee
    else:

        @wraps(callee)
        async def _async_callee(*args: Any, **kwargs: Any) -> Any:
            return await loop.run_in_executor(None, functools.partial(callee, *args, **kwargs))

        return _async_callee


def _get_next_function(h: Hookable, mw: Middleware, next: Callable[..., Any]) -> Callable[..., Any]:
    next = match_caller_type(callee=next, caller=mw.call)
    # next = match_caller_type(callee=next, caller=h._origin)
    call = match_caller_type(callee=mw.call, caller=h._origin)
    trigger = match_caller_type(callee=mw.trigger, caller=h._origin) if hasattr(mw, "trigger") else None

    @wraps(call)
    async def _chain_async(*args: Any, next: Callable[..., Any] = next, **kwargs: Any) -> Any:
        trigger_value = (await trigger(*args, **kwargs)) if trigger is not None else True
        if trigger_value:
            return await call(*args, next=next, **kwargs)
        else:
            return await next(*args, **kwargs)

    @wraps(call)
    def _chain_sync(*args: Any, next: Callable[..., Any] = next, **kwargs: Any) -> Any:
        if trigger is None or trigger(*args, **kwargs):
            return call(*args, next=next, **kwargs)
        else:
            return next(*args, **kwargs)

    return _chain_async if inspect.iscoroutinefunction(h._origin) else _chain_sync


def _build_middleware_chain(h: Hookable) -> None:
    next = h._origin
    for mw in reversed(h._middlewares):
        next = _get_next_function(h, mw, next)
        mw._chained_call = next  # type: ignore[attr-defined]

    h._chained_call = next  # type: ignore[misc]


def _check_middleware(h: Hookable, mw: Middleware) -> None:
    if inspect.iscoroutinefunction(mw.call) and not inspect.iscoroutinefunction(h):
        raise TypeError(f"Cannot use middleare with async `call` method on a sync hookable function: {mw=}, {h=} ")
    if hasattr(mw, "trigger") and inspect.iscoroutinefunction(mw.trigger) and not inspect.iscoroutinefunction(h):
        raise TypeError(f"Cannot use middleare with async `trigger` method on a sync hookable function: {mw=}, {h=} ")


def add_middleware(h: Callable[..., Any], mw: Middleware, *, position: Optional[int] = None) -> None:
    """Add a middleware to a hookable function.

    Args:
        h: The hookable function.
        mw: The middleware to add.
        position: The position to insert the middleware at. If `None`, then the middleware is appended to the end.

    Raises:
        TypeError: If the middleware cannot be used with the hookable function due to hookable function `h` being sync
            and `ws.call`` being async function.
    """
    _h: Hookable = h  # type: ignore[assignment]

    _check_middleware(_h, mw)

    if position is None:
        _h._middlewares.append(mw)
    else:
        _h._middlewares.insert(position, mw)

    # we could update the cain inplace, but this is a more robust solution
    _build_middleware_chain(_h)


def set_middlewares(h: Callable[..., Any], mws: List[Middleware]) -> None:
    """Set the middlewares for a hookable function.

    Args:
        h: The hookable function.
        mws: The middlewares to set.

    Raises:
        TypeError: If any of the middlewares cannot be used with the hookable function due to hookable function `h`
            being sync and `mw.call`` being async function for any `mw in mws`.

    """
    _h: Hookable = h  # type: ignore[assignment]

    for mw in mws:
        _check_middleware(_h, mw)

    _h._middlewares = mws  # type: ignore[misc]

    _build_middleware_chain(_h)
