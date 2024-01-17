import asyncio
import functools
import inspect
from typing import Any, Awaitable, Callable, Optional, Type
from unittest.mock import AsyncMock, MagicMock

import pytest
from autogen.asyncio_utils import sync_to_async

from autogen.middleware.base import (
    MiddlewareCallable,
    _check_middleware,
    _get_next_function,
    add_middleware,
    register_for_middleware,
    set_middlewares,
)


class MyMiddlewareSync:
    def __init__(self, name: str) -> None:
        self.name = name

    def call(self, *args: Any, next: Callable[..., Any], **kwargs: Any) -> str:
        retval = next(*args, **kwargs)
        return f"{self.name}.{format_function(MyMiddlewareSync.call, retval)}"

    def __eq__(self, value: object) -> bool:
        return isinstance(value, MyMiddlewareSync) and self.name == value.name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"


class MyMiddlewareAsync:
    def __init__(self, name: str) -> None:
        self.name = name

    async def call(self, *args: Any, next: Callable[..., Any], **kwargs: Any) -> str:
        retval = await next(*args, **kwargs)
        return f"{self.name}.{format_function(MyMiddlewareAsync.call, retval)}"

    def __eq__(self, value: object) -> bool:
        return isinstance(value, MyMiddlewareAsync) and self.name == value.name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"


def format_function(f: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
    return f"{f.__name__}(" + ", ".join([str(a) for a in args] + [f"{k}={v}" for k, v in kwargs.items()]) + ")"


def test_format_function() -> None:
    def f(*args: Any, **kwargs: Any) -> Any:
        return format_function(f, *args, **kwargs)

    assert f(1, 2, 3, a=4, b=5) == "f(1, 2, 3, a=4, b=5)"


def run_in_thread_pool(f: Callable[..., Any], *args: Any, **kwargs: Any) -> Awaitable[Any]:
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(None, functools.partial(f, *args, **kwargs))


@pytest.mark.asyncio()
async def test_middlewares_simple_sync() -> None:
    @register_for_middleware
    def f(msg: str) -> str:
        return f"Hello {msg}!"

    assert not inspect.iscoroutinefunction(f)
    assert f("world") == "Hello world!"

    assert f._middlewares == []

    add_middleware(f, MyMiddlewareSync("a"))
    assert f._middlewares == [MyMiddlewareSync("a")]
    actual = f("world")
    expected = "a.call(Hello world!)"
    assert actual == expected


@pytest.mark.asyncio()
async def test_middlewares() -> None:
    @register_for_middleware
    def f(*args: Any, **kwargs: Any) -> str:
        return format_function(f, *args, **kwargs)

    assert not inspect.iscoroutinefunction(f)
    assert f(1, 2, 3, a=4, b=5) == "f(1, 2, 3, a=4, b=5)"

    @register_for_middleware
    async def a_f(*args: Any, **kwargs: Any) -> str:
        return format_function(a_f, *args, **kwargs)

    assert inspect.iscoroutinefunction(a_f)
    assert await a_f(1, 2, 3, a=4, b=5) == "a_f(1, 2, 3, a=4, b=5)"

    assert f._middlewares == []
    assert a_f._middlewares == []

    add_middleware(f, MyMiddlewareSync("a"))
    assert f._middlewares == [MyMiddlewareSync("a")]
    assert f(1, 2, 3, a=4, b=5) == "a.call(f(1, 2, 3, a=4, b=5))"

    add_middleware(a_f, MyMiddlewareAsync("a_a"))
    assert a_f._middlewares == [MyMiddlewareAsync("a_a")]
    assert await a_f(1, 2, 3, a=4, b=5) == "a_a.call(a_f(1, 2, 3, a=4, b=5))"

    add_middleware(f, MyMiddlewareSync("b"))
    assert f._middlewares == [MyMiddlewareSync("a"), MyMiddlewareSync("b")]
    assert f(1, 2, 3, a=4, b=5) == "a.call(b.call(f(1, 2, 3, a=4, b=5)))"

    add_middleware(f, MyMiddlewareSync("c"))
    assert f._middlewares == [MyMiddlewareSync("a"), MyMiddlewareSync("b"), MyMiddlewareSync("c")]
    assert f(1, 2, 3, a=4, b=5) == "a.call(b.call(c.call(f(1, 2, 3, a=4, b=5))))"

    add_middleware(f, MyMiddlewareSync("A"), position=0)
    assert f._middlewares == [
        MyMiddlewareSync("A"),
        MyMiddlewareSync("a"),
        MyMiddlewareSync("b"),
        MyMiddlewareSync("c"),
    ]
    assert f(1, 2, 3, a=4, b=5) == "A.call(a.call(b.call(c.call(f(1, 2, 3, a=4, b=5)))))"

    add_middleware(f, MyMiddlewareSync("B"), position=2)
    assert f._middlewares == [
        MyMiddlewareSync("A"),
        MyMiddlewareSync("a"),
        MyMiddlewareSync("B"),
        MyMiddlewareSync("b"),
        MyMiddlewareSync("c"),
    ]
    assert f(1, 2, 3, a=4, b=5) == "A.call(a.call(B.call(b.call(c.call(f(1, 2, 3, a=4, b=5))))))"

    add_middleware(f, MyMiddlewareSync("C"), position=-1)
    assert f._middlewares == [
        MyMiddlewareSync("A"),
        MyMiddlewareSync("a"),
        MyMiddlewareSync("B"),
        MyMiddlewareSync("b"),
        MyMiddlewareSync("C"),
        MyMiddlewareSync("c"),
    ]
    assert f(1, 2, 3, a=4, b=5) == "A.call(a.call(B.call(b.call(C.call(c.call(f(1, 2, 3, a=4, b=5)))))))"

    add_middleware(f, MyMiddlewareSync("D"), position=6)
    assert f._middlewares == [
        MyMiddlewareSync("A"),
        MyMiddlewareSync("a"),
        MyMiddlewareSync("B"),
        MyMiddlewareSync("b"),
        MyMiddlewareSync("C"),
        MyMiddlewareSync("c"),
        MyMiddlewareSync("D"),
    ]
    assert f(1, 2, 3, a=4, b=5) == "A.call(a.call(B.call(b.call(C.call(c.call(D.call(f(1, 2, 3, a=4, b=5))))))))"


def get_mw(trigger_value: bool, is_async: bool) -> Type[Any]:
    class MyMiddlewareSyncTrigger(MyMiddlewareSync):
        def trigger(self, *args: Any, **kwargs: Any) -> bool:
            return trigger_value

    class MyMiddlewareAsyncTrigger(MyMiddlewareAsync):
        async def trigger(self, *args: Any, **kwargs: Any) -> bool:
            return trigger_value

    if trigger_value is None:
        return MyMiddlewareAsync if is_async else MyMiddlewareSync
    else:
        return MyMiddlewareAsyncTrigger if is_async else MyMiddlewareSyncTrigger


@pytest.mark.parametrize("trigger_value", [None, True, False])
@pytest.mark.asyncio()
async def test__get_next_function(trigger_value: bool) -> None:
    mw = get_mw(trigger_value, False)("mw")
    amw = get_mw(trigger_value, True)("amw")

    @register_for_middleware
    def f(*args: Any, **kwargs: Any) -> Any:
        return format_function(f, *args, **kwargs)

    @register_for_middleware
    async def a_f(*args: Any, **kwargs: Any) -> Any:
        return format_function(a_f, *args, **kwargs)

    next_mock = MagicMock(return_value="next_mock(...)")
    next_f = _get_next_function(f, mw, next_mock)
    if trigger_value is False:
        assert next_f(1, 2, 3, a=4, b=5) == "next_mock(...)"
    else:
        assert next_f(1, 2, 3, a=4, b=5) == "mw.call(next_mock(...))"
    next_mock.assert_called_once_with(1, 2, 3, a=4, b=5)

    next_mock = MagicMock(return_value="next_mock(...)")
    next_f = _get_next_function(f, amw, next_mock)
    assert not inspect.iscoroutinefunction(next_f)
    # sync next_f -> async amw.call -> sync next_mock
    actual = await sync_to_async()(next_f)(1, 2, 3, a=4, b=5)
    expected = "next_mock(...)" if trigger_value is False else "amw.call(next_mock(...))"
    assert actual == expected
    next_mock.assert_called_once_with(1, 2, 3, a=4, b=5)

    a_next_mock = AsyncMock(return_value="a_next_mock(...)")
    a_next_f = _get_next_function(a_f, amw, a_next_mock)
    expected = "a_next_mock(...)" if trigger_value is False else "amw.call(a_next_mock(...))"
    actual = await a_next_f(1, 2, 3, a=4, b=5)
    assert actual == expected
    a_next_mock.assert_awaited_once_with(1, 2, 3, a=4, b=5)

    a_next_mock = AsyncMock(return_value="a_next_mock(...)")
    # with pytest.raises(NotImplementedError) as e:
    a_next_f = _get_next_function(a_f, mw, a_next_mock)
    expected = "a_next_mock(...)" if trigger_value is False else "mw.call(a_next_mock(...))"
    actual = await a_next_f(1, 2, 3, a=4, b=5)
    assert actual == expected
    # assert await a_next_f(1, 2, 3, a=4, b=5) == "mw.call(a_next_mock(...))"
    a_next_mock.assert_awaited_once_with(1, 2, 3, a=4, b=5)


@pytest.mark.parametrize("trigger_value", [None, True, False])
def test__check_middleware(trigger_value: bool) -> None:
    @register_for_middleware
    def g(*args: Any, **kwargs: Any) -> Any:
        return format_function(g, *args, **kwargs)

    @register_for_middleware
    async def a_g(*args: Any, **kwargs: Any) -> Any:
        return format_function(a_g, *args, **kwargs)

    assert inspect.iscoroutinefunction(a_g)
    mw = get_mw(trigger_value, False)("mw")
    amw = get_mw(trigger_value, True)("amw")

    _check_middleware(g, mw)
    with pytest.raises(TypeError) as e:
        _check_middleware(g, amw)
    assert "Cannot use middleare with async `call` method on a sync hookable function" in str(e.value)
    _check_middleware(a_g, amw)
    _check_middleware(a_g, mw)


@pytest.mark.asyncio()
async def test__check_middleware_trigger() -> None:
    class MyMiddlewareSyncWithAsyncTrigger(MyMiddlewareSync):
        async def trigger(self, *args: Any, **kwargs: Any) -> bool:
            return True

    @register_for_middleware
    def f(*args: Any, **kwargs: Any) -> Any:
        return format_function(f, *args, **kwargs)

    broken_mw = MyMiddlewareSyncWithAsyncTrigger("broken_mw")

    with pytest.raises(TypeError) as e:
        _check_middleware(f, broken_mw)

    assert "Cannot use middleare with async `trigger` method on a sync hookable function" in str(e.value)


@pytest.mark.asyncio()
async def test_set_middlewares() -> None:
    @register_for_middleware
    def f(*args: Any, **kwargs: Any) -> str:
        return format_function(f, *args, **kwargs)

    assert not inspect.iscoroutinefunction(f)
    assert f(1, 2, 3, a=4, b=5) == "f(1, 2, 3, a=4, b=5)"

    @register_for_middleware
    async def a_f(*args: Any, **kwargs: Any) -> str:
        return format_function(a_f, *args, **kwargs)

    assert inspect.iscoroutinefunction(a_f)
    assert await a_f(1, 2, 3, a=4, b=5) == "a_f(1, 2, 3, a=4, b=5)"

    assert f._middlewares == []
    assert a_f._middlewares == []

    mws_sync = [MyMiddlewareSync("a"), MyMiddlewareSync("b"), MyMiddlewareSync("c")]
    set_middlewares(f, mws_sync)
    assert f._middlewares == [MyMiddlewareSync("a"), MyMiddlewareSync("b"), MyMiddlewareSync("c")]
    assert f(1, 2, 3, a=4, b=5) == "a.call(b.call(c.call(f(1, 2, 3, a=4, b=5))))"

    mws_async = [MyMiddlewareAsync("a_a"), MyMiddlewareAsync("a_b"), MyMiddlewareAsync("a_c")]
    set_middlewares(a_f, mws_async)
    assert a_f._middlewares == [MyMiddlewareAsync("a_a"), MyMiddlewareAsync("a_b"), MyMiddlewareAsync("a_c")]
    assert await a_f(1, 2, 3, a=4, b=5) == "a_a.call(a_b.call(a_c.call(a_f(1, 2, 3, a=4, b=5))))"


def test_example() -> None:
    class A:
        def __init__(self, name: str) -> None:
            self.name = name

        @register_for_middleware
        def process_message(self, msg: str, skip_middleware: Optional[bool] = None) -> str:
            return f"{self.name}.process_message({msg=})"

    class MyMiddleware:
        def __init__(self, name: str) -> None:
            self.name = name

        def call(self, *args: Any, next: Callable[..., Any], **kwargs: Any) -> str:
            retval = next(*args, **kwargs)
            return f"{self.name}.{format_function(self.call, retval)}"

        def trigger(self, *args: Any, **kwargs: Any) -> bool:
            return not ("skip_middleware" in kwargs and kwargs["skip_middleware"])

    a = A("a")
    add_middleware(A.process_message, MyMiddleware("mw"))

    assert a.process_message("hello") == "mw.call(a.process_message(msg='hello'))"
    assert a.process_message("hello", skip_middleware=False) == "mw.call(a.process_message(msg='hello'))"
    assert a.process_message("hello", skip_middleware=True) == "a.process_message(msg='hello')"

    add_middleware(A.process_message, MyMiddleware("MW"))
    assert a.process_message("hello") == "mw.call(MW.call(a.process_message(msg='hello')))"
