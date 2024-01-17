import asyncio
from functools import partial, wraps
import inspect

from typing import Any, Awaitable, Callable, List, Optional, Union

from typing_extensions import TypeVar

__all__ = ["async_to_sync", "match_caller_type", "sync_to_async"]

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def sync_to_async(*, loop: Optional[asyncio.AbstractEventLoop] = None) -> Callable[[F], F]:
    """Decorator to convert a sync function to async.

    Sync function f will be run in a thread pool executor, while an async function that awaits the result is returned.

    This is a fast way to support IO bound sync functions in async code, although there is some overhead to it. It is
    also absolutely necessary to support the use case where a sync function is calling async functions. Then the calling sync
    function must be run in a thread pool executor as it would block running loop otherwise.

    You can use chains of function created with `sync_to_async` and `async_to_sync` to execute a mix of sync and async
    functions calling each other.

    Args:
        f: The function to convert.
        loop: The event loop to run the function in. If not set, the current running loop is used.

    Returns:
        An async function that calls `f` and awaits the result.

    Raises:
        RuntimeError: If no running event loop is found.
        TypeError: If the function is already async.
    """
    loop = asyncio.get_running_loop() if loop is None else loop
    if loop is None:
        raise RuntimeError("No running event loop found.")  # pragma: no cover

    def _sync_to_async(f: F) -> F:
        if inspect.iscoroutinefunction(f):
            raise TypeError("Cannot convert async function to sync.")

        @wraps(f)
        async def _a_f(*args: Any, **kwargs: Any) -> Any:
            return await loop.run_in_executor(None, partial(f, *args, **kwargs))

        return _a_f  # type: ignore [return-value]

    return _sync_to_async


def async_to_sync(
    *, loop: Optional[asyncio.AbstractEventLoop] = None, timeout: Optional[float] = None
) -> Callable[[F], F]:
    """Decorator to convert an async function to sync.

    Async function f will be run in the event loop using `asyncio.run_coroutine_threadsafe`, while a sync function
    that blocks until the result is returned. This function will block the thread it is called from until the async
    function completes. If the async function is not awaited, then it will never complete. If the async function is
    awaited, then it will block the thread until the async function completes.

    Optionally, a timeout can be specified. If the async function does not complete within the timeout, then a
    `TimeoutError` is raised.

    This is a fast way to support IO bound async functions in sync code, although there is some overhead to it. It is
    also absolutely necessary to support the use case where an async function is calling sync functions. Then the calling
    async function must be run in the event loop as it would block the running thread otherwise.

    You can use chains of function created with `sync_to_async` and `async_to_sync` to execute a mix of sync and async
    functions calling each other.

    Args:
        f: The function to convert.
        loop: The event loop to run the function in. If not set, the current running loop is used.
        timeout: If not None, the timeout to use when waiting for the result of `f`.

    Returns:
        A sync function that calls `f` and blocks until the result is available.

    Raises:
        RuntimeError: If no running event loop is found.
        TimeoutError: If the async function does not complete within the timeout.
        TypeError: If the function is already sync.
    """
    loop = asyncio.get_running_loop() if loop is None else loop
    if loop is None:
        raise RuntimeError("No running event loop found.")  # pragma: no cover

    def _async_to_sync(f: F) -> F:
        if not inspect.iscoroutinefunction(f):
            raise TypeError("Cannot convert sync function to async.")

        @wraps(f)
        def _s_f(*args: Any, **kwargs: Any) -> Any:
            coro = f(*args, **kwargs)
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(
                # If not None, it will block until the coroutine has completed or the timeout is reached
                timeout=timeout
            )

        return _s_f  # type: ignore [return-value]

    return _async_to_sync


def match_caller_type(
    *,
    callee: F,
    caller: Callable[..., Any],
    loop: Optional[asyncio.AbstractEventLoop] = None,
    timeout: Optional[float] = None
) -> F:
    """Modify callee to have the same sync/async type as caller if necessary.

    If both `callee` and `caller` are both async or both sync functions, then `callee` is returned.
    If `callee` is sync and `caller` is async, then a wrapper is returned that calls `callee` and awaits the result.
    If `callee` is async and `caller` is sync, a wrapper is returned that waits for `callee` and returns the result.

    Args:
        callee: The source function.
        caller: The destination function.
        loop: The event loop to run the function in. If not set, the current running loop is used.
        timeout: If not None, the timeout to use when waiting for the result of `callee`. It is only available if the
            caller is a `sync` function and the callee is an `async` function.

    Returns:
        A function that matches the caller type of `caller`.

    Raises:
        TimeoutError: If the async function `callee` does not complete within the timeout.
    """
    # return the callee if already the same type
    if inspect.iscoroutinefunction(caller) == inspect.iscoroutinefunction(callee):
        return callee

    loop = asyncio.get_running_loop() if loop is None else loop

    return (
        async_to_sync(loop=loop, timeout=timeout)(callee)
        if inspect.iscoroutinefunction(callee)
        else sync_to_async(loop=loop)(callee)
    )
