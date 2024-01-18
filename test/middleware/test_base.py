import asyncio
import functools
import inspect
from typing import Any, Awaitable, Callable, Optional, Type
from unittest.mock import AsyncMock, MagicMock

import pytest

from autogen.asyncio_utils import sync_to_async
from autogen.middleware.base import (
    MiddlewareCallable,
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
    class A:
        @register_for_middleware
        def f(self, msg: str) -> str:
            return f"Hello {msg}!"

    a = A()
    assert not inspect.iscoroutinefunction(a.f)
    assert a.f("world") == "Hello world!"

    assert a.f._middlewares == {}  # type: ignore[attr-defined]

    add_middleware(a.f, MyMiddlewareSync("a"))
    assert a.f._middlewares == {a: [MyMiddlewareSync("a")]}  # type: ignore[attr-defined]
    actual = a.f("world")
    expected = "a.call(Hello world!)"
    assert actual == expected


@pytest.mark.asyncio()
async def test_middlewares() -> None:
    class A:
        @register_for_middleware
        def f(self, *args: Any, **kwargs: Any) -> str:
            return format_function(A.f, *args, **kwargs)

        @register_for_middleware
        async def a_f(self, *args: Any, **kwargs: Any) -> str:
            return format_function(A.a_f, *args, **kwargs)

    a = A()
    assert not inspect.iscoroutinefunction(a.f)
    assert a.f(1, 2, 3, a=4, b=5) == "f(1, 2, 3, a=4, b=5)"

    assert inspect.iscoroutinefunction(a.a_f)
    assert await a.a_f(1, 2, 3, a=4, b=5) == "a_f(1, 2, 3, a=4, b=5)"

    assert a.f._middlewares == {}  # type: ignore[attr-defined]
    assert a.a_f._middlewares == {}  # type: ignore[attr-defined]

    add_middleware(a.f, MyMiddlewareSync("a"))
    assert a.f._middlewares[a] == [MyMiddlewareSync("a")]  # type: ignore[attr-defined]
    assert A.f._middlewares[a] == [MyMiddlewareSync("a")]  # type: ignore[attr-defined]
    assert a.f(1, 2, 3, a=4, b=5) == "a.call(f(1, 2, 3, a=4, b=5))"

    add_middleware(a.a_f, MyMiddlewareAsync("a_a"))
    assert a.a_f._middlewares[a] == [MyMiddlewareAsync("a_a")]  # type: ignore[attr-defined]
    assert await a.a_f(1, 2, 3, a=4, b=5) == "a_a.call(a_f(1, 2, 3, a=4, b=5))"

    add_middleware(a.f, MyMiddlewareSync("b"))
    assert a.f._middlewares[a] == [MyMiddlewareSync("a"), MyMiddlewareSync("b")]  # type: ignore[attr-defined]
    assert a.f(1, 2, 3, a=4, b=5) == "a.call(b.call(f(1, 2, 3, a=4, b=5)))"

    add_middleware(a.f, MyMiddlewareSync("c"))
    assert a.f._middlewares[a] == [MyMiddlewareSync("a"), MyMiddlewareSync("b"), MyMiddlewareSync("c")]  # type: ignore[attr-defined]
    assert a.f(1, 2, 3, a=4, b=5) == "a.call(b.call(c.call(f(1, 2, 3, a=4, b=5))))"

    add_middleware(a.f, MyMiddlewareSync("A"), position=0)
    assert a.f._middlewares[a] == [  # type: ignore[attr-defined]
        MyMiddlewareSync("A"),
        MyMiddlewareSync("a"),
        MyMiddlewareSync("b"),
        MyMiddlewareSync("c"),
    ]
    assert a.f(1, 2, 3, a=4, b=5) == "A.call(a.call(b.call(c.call(f(1, 2, 3, a=4, b=5)))))"

    add_middleware(a.f, MyMiddlewareSync("B"), position=2)
    assert a.f._middlewares[a] == [  # type: ignore[attr-defined]
        MyMiddlewareSync("A"),
        MyMiddlewareSync("a"),
        MyMiddlewareSync("B"),
        MyMiddlewareSync("b"),
        MyMiddlewareSync("c"),
    ]
    assert a.f(1, 2, 3, a=4, b=5) == "A.call(a.call(B.call(b.call(c.call(f(1, 2, 3, a=4, b=5))))))"

    add_middleware(a.f, MyMiddlewareSync("C"), position=-1)
    assert a.f._middlewares[a] == [  # type: ignore[attr-defined]
        MyMiddlewareSync("A"),
        MyMiddlewareSync("a"),
        MyMiddlewareSync("B"),
        MyMiddlewareSync("b"),
        MyMiddlewareSync("C"),
        MyMiddlewareSync("c"),
    ]
    assert a.f(1, 2, 3, a=4, b=5) == "A.call(a.call(B.call(b.call(C.call(c.call(f(1, 2, 3, a=4, b=5)))))))"

    add_middleware(a.f, MyMiddlewareSync("D"), position=6)
    assert a.f._middlewares[a] == [  # type: ignore[attr-defined]
        MyMiddlewareSync("A"),
        MyMiddlewareSync("a"),
        MyMiddlewareSync("B"),
        MyMiddlewareSync("b"),
        MyMiddlewareSync("C"),
        MyMiddlewareSync("c"),
        MyMiddlewareSync("D"),
    ]
    assert a.f(1, 2, 3, a=4, b=5) == "A.call(a.call(B.call(b.call(C.call(c.call(D.call(f(1, 2, 3, a=4, b=5))))))))"


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
    next_f = _get_next_function(f, mw, next_mock)  # type: ignore[arg-type]
    if trigger_value is False:
        assert next_f(1, 2, 3, a=4, b=5) == "next_mock(...)"
    else:
        assert next_f(1, 2, 3, a=4, b=5) == "mw.call(next_mock(...))"
    next_mock.assert_called_once_with(1, 2, 3, a=4, b=5)

    next_mock = MagicMock(return_value="next_mock(...)")
    next_f = _get_next_function(f, amw, next_mock)  # type: ignore[arg-type]
    assert not inspect.iscoroutinefunction(next_f)
    # sync next_f -> async amw.call -> sync next_mock
    actual = await sync_to_async()(next_f)(1, 2, 3, a=4, b=5)
    expected = "next_mock(...)" if trigger_value is False else "amw.call(next_mock(...))"
    assert actual == expected
    next_mock.assert_called_once_with(1, 2, 3, a=4, b=5)

    a_next_mock = AsyncMock(return_value="a_next_mock(...)")
    a_next_f = _get_next_function(a_f, amw, a_next_mock)  # type: ignore[arg-type]
    expected = "a_next_mock(...)" if trigger_value is False else "amw.call(a_next_mock(...))"
    actual = await a_next_f(1, 2, 3, a=4, b=5)
    assert actual == expected
    a_next_mock.assert_awaited_once_with(1, 2, 3, a=4, b=5)

    a_next_mock = AsyncMock(return_value="a_next_mock(...)")
    # with pytest.raises(NotImplementedError) as e:
    a_next_f = _get_next_function(a_f, mw, a_next_mock)  # type: ignore[arg-type]
    expected = "a_next_mock(...)" if trigger_value is False else "mw.call(a_next_mock(...))"
    actual = await a_next_f(1, 2, 3, a=4, b=5)
    assert actual == expected
    # assert await a_next_f(1, 2, 3, a=4, b=5) == "mw.call(a_next_mock(...))"
    a_next_mock.assert_awaited_once_with(1, 2, 3, a=4, b=5)


@pytest.mark.asyncio()
async def test_set_middlewares() -> None:
    class A:
        @register_for_middleware
        def f(self, *args: Any, **kwargs: Any) -> str:
            return format_function(A.f, *args, **kwargs)

        @register_for_middleware
        async def a_f(self, *args: Any, **kwargs: Any) -> str:
            return format_function(A.a_f, *args, **kwargs)

    assert not inspect.iscoroutinefunction(A.f)
    a = A()
    assert not inspect.iscoroutinefunction(a.f)
    assert a.f(1, 2, 3, a=4, b=5) == "f(1, 2, 3, a=4, b=5)"

    assert inspect.iscoroutinefunction(a.a_f)
    assert await a.a_f(1, 2, 3, a=4, b=5) == "a_f(1, 2, 3, a=4, b=5)"

    assert a.f._middlewares == {}  # type: ignore[attr-defined]
    assert a.a_f._middlewares == {}  # type: ignore[attr-defined]

    mws_sync = [MyMiddlewareSync("a"), MyMiddlewareSync("b"), MyMiddlewareSync("c")]
    set_middlewares(a.f, mws_sync)
    assert A.f._middlewares[a] == [MyMiddlewareSync("a"), MyMiddlewareSync("b"), MyMiddlewareSync("c")]  # type: ignore[attr-defined]
    assert a.f(1, 2, 3, a=4, b=5) == "a.call(b.call(c.call(f(1, 2, 3, a=4, b=5))))"

    mws_async = [MyMiddlewareAsync("a_a"), MyMiddlewareAsync("a_b"), MyMiddlewareAsync("a_c")]
    set_middlewares(a.a_f, mws_async)
    assert A.a_f._middlewares[a] == [MyMiddlewareAsync("a_a"), MyMiddlewareAsync("a_b"), MyMiddlewareAsync("a_c")]  # type: ignore[attr-defined]
    assert await a.a_f(1, 2, 3, a=4, b=5) == "a_a.call(a_b.call(a_c.call(a_f(1, 2, 3, a=4, b=5))))"


def test_integration() -> None:
    class A:
        def __init__(self, name: str) -> None:
            self.name = name

        @register_for_middleware
        def process_message(self, msg: str, skip_middleware: Optional[bool] = None) -> str:
            return f"{self.name}.process_message({msg=})"

    assert hasattr(A.process_message, "_origin")
    assert hasattr(A.process_message, "_chained_call")

    def is_bound_method(method: Callable[..., Any]) -> bool:
        return hasattr(method, "__self__") and method.__self__ is not None

    print(f"{is_bound_method(A.process_message)=}")
    print(f"{is_bound_method(A(name='a').process_message)=}")

    class MyMiddleware:
        def __init__(self, name: str) -> None:
            self.name = name

        def call(self, *args: Any, next: Callable[..., Any], **kwargs: Any) -> str:
            retval = next(*args, **kwargs)
            return f"{self.name}.{format_function(self.call, retval)}"

        def trigger(self, *args: Any, **kwargs: Any) -> bool:
            return not ("skip_middleware" in kwargs and kwargs["skip_middleware"])

    a = A("a")
    mw = MyMiddleware("mw")

    assert a.process_message("hello") == "a.process_message(msg='hello')"

    add_middleware(a.process_message, mw)

    h: MiddlewareCallable = a.process_message  # type: ignore[assignment]
    assert hasattr(h, "_origin")
    assert hasattr(h, "_chained_call")
    assert isinstance(h._chained_call, dict)
    assert a in h._chained_call.keys()
    assert hasattr(h._chained_call[a], "__call__")

    actual = a.process_message("hello")
    expected = "mw.call(a.process_message(msg='hello'))"
    assert actual == expected, actual

    assert h._middlewares[a] == [mw]  # type: ignore[comparison-overlap]

    mw2 = MyMiddleware("mw2")
    add_middleware(a.process_message, mw2)
    actual = a.process_message("hello")
    expected = "mw.call(mw2.call(a.process_message(msg='hello')))"
    assert actual == expected, actual

    b = A("b")
    with pytest.raises(ValueError):
        add_middleware(b.process_message, mw)

    mwb = MyMiddleware("mwb")
    add_middleware(b.process_message, mwb)

    actual = b.process_message("hello")
    expected = "mwb.call(b.process_message(msg='hello'))"
    assert actual == expected, actual

    actual = a.process_message("hello")
    expected = "mw.call(mw2.call(a.process_message(msg='hello')))"
    assert actual == expected, actual


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
    add_middleware(a.process_message, MyMiddleware("mw"))

    assert a.process_message("hello") == "mw.call(a.process_message(msg='hello'))"
    assert a.process_message("hello", skip_middleware=False) == "mw.call(a.process_message(msg='hello'))"
    assert a.process_message("hello", skip_middleware=True) == "a.process_message(msg='hello')"

    add_middleware(a.process_message, MyMiddleware("MW"))
    assert a.process_message("hello") == "mw.call(MW.call(a.process_message(msg='hello')))"
