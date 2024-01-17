import inspect
from typing import Any, Callable

import pytest

from autogen.asyncio_utils import async_to_sync, match_caller_type, sync_to_async


def format_function(f: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
    return f"{f.__name__}(" + ", ".join([str(a) for a in args] + [f"{k}={v}" for k, v in kwargs.items()]) + ")"


@pytest.mark.asyncio()
async def test_sync_to_async() -> None:
    @sync_to_async()
    def f(*args: Any, **kwargs: Any) -> Any:
        return format_function(f, *args, **kwargs)

    assert inspect.iscoroutinefunction(f)
    assert await f(1, 2, 3, a=4, b=5) == "f(1, 2, 3, a=4, b=5)"


@pytest.mark.asyncio()
async def test_async_to_sync() -> None:
    @async_to_sync(timeout=2)
    async def a_f(*args: Any, **kwargs: Any) -> Any:
        return format_function(a_f, *args, **kwargs)

    assert not inspect.iscoroutinefunction(a_f)

    a_a_f = sync_to_async()(a_f)

    assert await a_a_f(1, 2, 3, a=4, b=5) == "a_f(1, 2, 3, a=4, b=5)"


@pytest.mark.asyncio()
async def test_match_caller_type() -> None:
    def f(*args: Any, **kwargs: Any) -> Any:
        return format_function(f, *args, **kwargs)

    async def a_f(*args: Any, **kwargs: Any) -> Any:
        return format_function(a_f, *args, **kwargs)

    assert match_caller_type(callee=f, caller=f) == f
    assert match_caller_type(callee=a_f, caller=a_f) == a_f

    a_f2 = match_caller_type(callee=f, caller=a_f)
    assert inspect.iscoroutinefunction(a_f2)
    assert await a_f2(1, 2, 3, a=4, b=5) == "f(1, 2, 3, a=4, b=5)"

    f3 = match_caller_type(callee=a_f, caller=f)
    assert not inspect.iscoroutinefunction(f3)
    a_f3 = sync_to_async()(f3)
    assert await a_f3(1, 2, 3, a=4, b=5) == "a_f(1, 2, 3, a=4, b=5)"
