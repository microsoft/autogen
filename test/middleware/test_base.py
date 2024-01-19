import asyncio
import functools
import inspect
from typing import Any, Awaitable, Callable, Optional, Type
from unittest.mock import AsyncMock, MagicMock

import pytest

from autogen.middleware.base import (
    _build_middleware_chain,
    _next_function_base,
    _next_function_step,
    _get_self_from_bound,
    _is_bound_to_instance_method,
    add_middleware,
    register_for_middleware,
    set_middlewares,
)


class MyMiddleware:
    def __init__(self, name: str) -> None:
        self.name = name

    def call(self, *args: Any, next: Callable[..., Any], **kwargs: Any) -> str:
        # print(f"MyMiddlewar.call: {next=}")
        # assert False, next
        retval = next(*args, **kwargs)
        return f"{self.name}.{format_function(MyMiddleware.call, retval)}"

    async def a_call(self, *args: Any, next: Callable[..., Any], **kwargs: Any) -> str:
        retval = await next(*args, **kwargs)
        return f"{self.name}.{format_function(MyMiddleware.call, retval)}"

    def __eq__(self, value: object) -> bool:
        return isinstance(value, MyMiddleware) and self.name == value.name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"


class IntMiddleware:
    def __init__(self, name: str) -> None:
        self.name = name

    def call(self, a: int, b: int = 2, c: int = 0, *, d: int, e: int = 5, f: int = 0, next: Callable[..., Any]) -> str:
        # print(f"MyMiddlewar.call: {next=}")
        # assert False, next
        retval = next(a, b, c, d=d, e=e, f=f)
        return f"{self.name}.{format_function(MyMiddleware.call, retval)}"

    async def a_call(
        self, a: int, b: int = 2, c: int = 0, *, d: int, e: int = 5, f: int = 0, next: Callable[..., Any]
    ) -> str:
        retval = await next(a, b, c, d=d, e=e, f=f)
        return f"{self.name}.{format_function(MyMiddleware.call, retval)}"

    def __eq__(self, value: object) -> bool:
        return isinstance(value, MyMiddleware) and self.name == value.name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"


def format_function(func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
    return f"{func.__name__}(" + ", ".join([str(a) for a in args] + [f"{k}={v}" for k, v in kwargs.items()]) + ")"


def test_format_function() -> None:
    def f(*args: Any, **kwargs: Any) -> Any:
        return format_function(f, *args, **kwargs)

    assert f(1, 2, 3, a=4, b=5) == "f(1, 2, 3, a=4, b=5)"


@pytest.mark.asyncio()
async def test_register_for_middleware() -> None:
    class A:
        @register_for_middleware
        def f(self, *args: Any, **kwargs: Any) -> str:
            return format_function(A.f, *args, **kwargs)

        @register_for_middleware
        async def a_f(self, *args: Any, **kwargs: Any) -> str:
            return format_function(A.a_f, *args, **kwargs)

    assert A.f._chained_calls == {}  # type: ignore[attr-defined]
    assert A.a_f._chained_calls == {}  # type: ignore[attr-defined]

    assert A.f._is_async is False  # type: ignore[attr-defined]
    assert A.a_f._is_async is True  # type: ignore[attr-defined]

    assert A.f._middlewares == {}  # type: ignore[attr-defined]
    assert A.a_f._middlewares == {}  # type: ignore[attr-defined]

    a = A()
    # we need to call _origin with self because it is not bound to an instance
    assert a.f._origin(a, 1, 2, a=3, b=4) == "f(1, 2, a=3, b=4)"  # type: ignore[attr-defined]
    assert await a.a_f._origin(a, 1, 2, a=3, b=4) == "a_f(1, 2, a=3, b=4)"  # type: ignore[attr-defined]

    assert a.f(1, 2, a=3, b=4) == "f(1, 2, a=3, b=4)"
    assert await a.a_f(1, 2, a=3, b=4) == "a_f(1, 2, a=3, b=4)"

    with pytest.raises(ValueError):

        class B:
            @register_for_middleware
            @classmethod
            def f(cls, *args: Any, **kwargs: Any) -> str:
                return format_function(B.f, *args, **kwargs)

    with pytest.raises(ValueError):

        class C:
            @register_for_middleware
            @staticmethod
            def f(*args: Any, **kwargs: Any) -> str:
                return format_function(C.f, *args, **kwargs)

        inspect.signature(C.f)

    with pytest.raises(ValueError):

        @register_for_middleware
        def g(*args: Any, **kwargs: Any) -> str:
            return format_function(g, *args, **kwargs)

    # we have to delay comprehensive testing register_for_middleware.h_sync and register_for_middleware.h_async
    # until we call add_middleware because we need to check if the function is bound to an instance


def test__is_bound_to_instance_method() -> None:
    class A:
        def f(self) -> None:
            pass

        @classmethod
        def g(cls) -> None:
            pass

        @staticmethod
        def h() -> None:
            pass

    def i() -> None:
        pass

    assert not _is_bound_to_instance_method(A.f)
    assert not _is_bound_to_instance_method(A.g)
    assert not _is_bound_to_instance_method(A.h)
    assert not _is_bound_to_instance_method(i)

    a = A()
    assert _is_bound_to_instance_method(a.f)
    assert not _is_bound_to_instance_method(a.g)
    assert not _is_bound_to_instance_method(a.h)
    assert not _is_bound_to_instance_method(i)


@pytest.mark.asyncio()
async def test__get_initial_next_function() -> None:
    class A:
        @register_for_middleware
        def f(self, a: int, b: int = 2, c: int = 0, *, d: int, e: int = 5, f: int = 0) -> str:
            return format_function(A.f, a, b, c, d=d, e=e, f=f)

        @register_for_middleware
        async def a_f(self, a: int, b: int = 2, c: int = 0, *, d: int, e: int = 5, f: int = 0) -> str:
            return format_function(A.a_f, a, b, c, d=d, e=e, f=f)

    a = A()
    mw = IntMiddleware("mw")
    mw._bound_h = a.f  # type: ignore[attr-defined]
    assert mw._bound_h(1, c=3, d=4, f=6) == "f(1, 2, 3, d=4, e=5, f=6)"  # type: ignore[attr-defined]

    initial_next = _next_function_base(mw=mw)  # type: ignore[arg-type]
    assert initial_next(1, c=3, d=4, f=6) == "f(1, 2, 3, d=4, e=5, f=6)"

    amw = MagicMock()
    amw._bound_h = a.a_f

    a_initial_next = _next_function_base(mw=amw)
    assert await a_initial_next(1, c=3, d=4, f=6) == "a_f(1, 2, 3, d=4, e=5, f=6)"


@pytest.mark.asyncio()
async def test__get_next_function() -> None:
    class A:
        @register_for_middleware
        def f(self, a: int, b: int = 2, c: int = 0, *, d: int, e: int = 5, f: int = 0) -> str:
            return format_function(A.f, a, b, c, d=d, e=e, f=f)

        @register_for_middleware
        async def a_f(self, a: int, b: int = 2, c: int = 0, *, d: int, e: int = 5, f: int = 0) -> str:
            return format_function(A.a_f, a, b, c, d=d, e=e, f=f)

    a = A()

    mw = IntMiddleware("mw")
    mw._bound_h = a.f  # type: ignore[attr-defined]
    initial_next = _next_function_base(mw=mw)  # type: ignore[arg-type]
    assert initial_next(1, c=3, d=4, f=6) == "f(1, 2, 3, d=4, e=5, f=6)"
    next = _next_function_step(mw=mw, next=initial_next)  # type: ignore[arg-type]
    assert next(1, c=3, d=4, f=6) == "mw.call(f(1, 2, 3, d=4, e=5, f=6))"

    mw2 = MyMiddleware("mw2")
    mw2._bound_h = a.f  # type: ignore[attr-defined]
    next = _next_function_step(mw=mw2, next=next)  # type: ignore[arg-type]
    assert next(1, c=3, d=4, f=6) == "mw2.call(mw.call(f(1, 2, 3, d=4, e=5, f=6)))"

    amw = MyMiddleware("amw")
    amw._bound_h = a.a_f  # type: ignore[attr-defined]
    a_initial_next = _next_function_base(mw=amw)  # type: ignore[arg-type]
    assert await a_initial_next(1, c=3, d=4, f=6) == "a_f(1, 2, 3, d=4, e=5, f=6)"
    a_next = _next_function_step(mw=amw, next=a_initial_next)  # type: ignore[arg-type]
    assert await a_next(1, c=3, d=4, f=6) == "amw.call(a_f(1, 2, 3, d=4, e=5, f=6))"

    amw2 = IntMiddleware("amw2")
    amw2._bound_h = a.a_f  # type: ignore[attr-defined]
    a_next = _next_function_step(mw=amw2, next=a_next)  # type: ignore[arg-type]
    assert await a_next(1, c=3, d=4, f=6) == "amw2.call(amw.call(a_f(1, 2, 3, d=4, e=5, f=6)))"


def test__get_self_from_bound() -> None:
    class A:
        def f(self) -> None:
            pass

        @classmethod
        def g(self) -> None:
            pass

        @staticmethod
        def h() -> None:
            pass

    a = A()
    assert _get_self_from_bound(a.f) == a

    with pytest.raises(ValueError):
        _get_self_from_bound(A.f)

    assert _get_self_from_bound(a.g) == A
    assert _get_self_from_bound(A.g) == A

    with pytest.raises(ValueError):
        _get_self_from_bound(A.h)


@pytest.mark.asyncio()
async def test__build_middleware_chain() -> None:
    class A:
        @register_for_middleware
        def f(self, a: int, b: int = 2, c: int = 0, *, d: int, e: int = 5, f: int = 0) -> str:
            print(f"A.f: {self=}")
            return format_function(A.f, a, b, c, d=d, e=e, f=f)

        @register_for_middleware
        async def a_f(self, a: int, b: int = 2, c: int = 0, *, d: int, e: int = 5, f: int = 0) -> str:
            return format_function(A.a_f, a, b, c, d=d, e=e, f=f)

    a = A()

    assert hasattr(A.f, "_origin")
    assert hasattr(a.f, "_origin")

    # sync cases
    mw = MyMiddleware("mw")
    mw._bound_h = a.f  # type: ignore[attr-defined]
    mw2 = IntMiddleware("mw2")
    mw2._bound_h = a.f  # type: ignore[attr-defined]

    a.f._middlewares[a] = []  # type: ignore[attr-defined]
    _build_middleware_chain(a.f)  # type: ignore[arg-type]
    assert mw._bound_h == a.f  # type: ignore[attr-defined]
    assert a.f._chained_calls == {}  # type: ignore[attr-defined]
    assert a.f(1, c=3, d=4, f=6) == "f(1, 2, 3, d=4, e=5, f=6)"

    a.f._middlewares[a] = [mw]  # type: ignore[attr-defined]
    _build_middleware_chain(a.f)  # type: ignore[arg-type]
    assert mw._bound_h == a.f  # type: ignore[attr-defined]
    assert a.f(1, c=3, d=4, f=6) == "mw.call(f(1, 2, 3, d=4, e=5, f=6))"

    a.f._middlewares[a] = [mw, mw2]  # type: ignore[attr-defined]
    _build_middleware_chain(a.f)  # type: ignore[arg-type]
    assert mw._bound_h == a.f  # type: ignore[attr-defined]
    assert mw2._bound_h == a.f  # type: ignore[attr-defined]
    assert a.f(1, c=3, d=4, f=6) == "mw.call(mw2.call(f(1, 2, 3, d=4, e=5, f=6)))"

    with pytest.raises(ValueError) as e:
        _build_middleware_chain(A.f)  # type: ignore[arg-type]
    assert "Middleware can only be added to bound methods." in str(e.value)

    # async cases
    amw = IntMiddleware("amw")
    amw._bound_h = a.a_f  # type: ignore[attr-defined]
    amw2 = MyMiddleware("amw2")
    amw2._bound_h = a.a_f  # type: ignore[attr-defined]

    a.a_f._middlewares[a] = []  # type: ignore[attr-defined]
    _build_middleware_chain(a.a_f)  # type: ignore[arg-type]
    assert amw._bound_h == a.a_f  # type: ignore[attr-defined]
    assert a.a_f._chained_calls == {}  # type: ignore[attr-defined]
    assert await a.a_f(1, c=3, d=4, f=6) == "a_f(1, 2, 3, d=4, e=5, f=6)"

    a.a_f._middlewares[a] = [amw]  # type: ignore[attr-defined]
    _build_middleware_chain(a.a_f)  # type: ignore[arg-type]
    assert amw._bound_h == a.a_f  # type: ignore[attr-defined]
    assert await a.a_f(1, c=3, d=4, f=6) == "amw.call(a_f(1, 2, 3, d=4, e=5, f=6))"

    a.a_f._middlewares[a] = [amw, amw2]  # type: ignore[attr-defined]
    _build_middleware_chain(a.a_f)  # type: ignore[arg-type]
    assert amw._bound_h == a.a_f  # type: ignore[attr-defined]
    assert amw2._bound_h == a.a_f  # type: ignore[attr-defined]
    assert await a.a_f(1, c=3, d=4, f=6) == "amw.call(amw2.call(a_f(1, 2, 3, d=4, e=5, f=6)))"

    # error handling
    with pytest.raises(ValueError) as e:
        _build_middleware_chain(A.f)  # type: ignore[arg-type]
    assert "Middleware can only be added to bound methods." in str(e.value)


@pytest.mark.asyncio()
async def test_add_middleware() -> None:
    class A:
        @register_for_middleware
        def f(self, a: int, b: int = 2, c: int = 0, *, d: int, e: int = 5, f: int = 0) -> str:
            print(f"A.f: {self=}")
            return format_function(A.f, a, b, c, d=d, e=e, f=f)

        @register_for_middleware
        async def a_f(self, a: int, b: int = 2, c: int = 0, *, d: int, e: int = 5, f: int = 0) -> str:
            return format_function(A.a_f, a, b, c, d=d, e=e, f=f)

    a = A()

    assert hasattr(A.f, "_origin")
    assert hasattr(a.f, "_origin")

    # sync cases
    mw = MyMiddleware("mw")
    mw2 = IntMiddleware("mw2")

    assert a.f._chained_calls == {}  # type: ignore[attr-defined]
    assert a.f(1, c=3, d=4, f=6) == "f(1, 2, 3, d=4, e=5, f=6)"

    add_middleware(a.f, mw)

    assert mw._bound_h == a.f  # type: ignore[attr-defined]
    assert a.f(1, c=3, d=4, f=6) == "mw.call(f(1, 2, 3, d=4, e=5, f=6))"

    add_middleware(a.f, mw2)

    assert mw._bound_h == a.f  # type: ignore[attr-defined]
    assert mw2._bound_h == a.f  # type: ignore[attr-defined]
    assert a.f(1, c=3, d=4, f=6) == "mw.call(mw2.call(f(1, 2, 3, d=4, e=5, f=6)))"

    with pytest.raises(ValueError) as e:
        _build_middleware_chain(A.f)  # type: ignore[arg-type]
    assert "Middleware can only be added to bound methods." in str(e.value)

    # async cases
    amw = IntMiddleware("amw")
    amw._bound_h = a.a_f  # type: ignore[attr-defined]
    amw2 = MyMiddleware("amw2")
    amw2._bound_h = a.a_f  # type: ignore[attr-defined]

    a.a_f._middlewares[a] = []  # type: ignore[attr-defined]
    assert a.a_f._chained_calls == {}  # type: ignore[attr-defined]
    assert await a.a_f(1, c=3, d=4, f=6) == "a_f(1, 2, 3, d=4, e=5, f=6)"

    add_middleware(a.a_f, amw)
    assert amw._bound_h == a.a_f  # type: ignore[attr-defined]
    assert await a.a_f(1, c=3, d=4, f=6) == "amw.call(a_f(1, 2, 3, d=4, e=5, f=6))"

    add_middleware(a.a_f, amw2)
    assert amw._bound_h == a.a_f  # type: ignore[attr-defined]
    assert amw2._bound_h == a.a_f  # type: ignore[attr-defined]
    assert await a.a_f(1, c=3, d=4, f=6) == "amw.call(amw2.call(a_f(1, 2, 3, d=4, e=5, f=6)))"

    # error handling
    with pytest.raises(ValueError) as e:
        _build_middleware_chain(A.f)  # type: ignore[arg-type]
    assert "Middleware can only be added to bound methods." in str(e.value)


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

    mws_sync = [MyMiddleware("a"), MyMiddleware("b"), MyMiddleware("c")]
    set_middlewares(a.f, mws_sync)
    assert A.f._middlewares[a] == [MyMiddleware("a"), MyMiddleware("b"), MyMiddleware("c")]  # type: ignore[attr-defined]
    assert a.f(1, 2, 3, a=4, b=5) == "a.call(b.call(c.call(f(1, 2, 3, a=4, b=5))))"

    mws_async = [MyMiddleware("a_a"), MyMiddleware("a_b"), MyMiddleware("a_c")]
    set_middlewares(a.a_f, mws_async)
    assert A.a_f._middlewares[a] == [MyMiddleware("a_a"), MyMiddleware("a_b"), MyMiddleware("a_c")]  # type: ignore[attr-defined]
    assert await a.a_f(1, 2, 3, a=4, b=5) == "a_a.call(a_b.call(a_c.call(a_f(1, 2, 3, a=4, b=5))))"


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

    add_middleware(a.f, MyMiddleware("a"))
    assert a.f._middlewares == {a: [MyMiddleware("a")]}  # type: ignore[attr-defined]
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

    add_middleware(a.f, MyMiddleware("a"))
    assert a.f._middlewares[a] == [MyMiddleware("a")]  # type: ignore[attr-defined]
    assert A.f._middlewares[a] == [MyMiddleware("a")]  # type: ignore[attr-defined]
    assert a.f(1, 2, 3, a=4, b=5) == "a.call(f(1, 2, 3, a=4, b=5))"

    add_middleware(a.a_f, MyMiddleware("a_a"))
    assert a.a_f._middlewares[a] == [MyMiddleware("a_a")]  # type: ignore[attr-defined]
    assert await a.a_f(1, 2, 3, a=4, b=5) == "a_a.call(a_f(1, 2, 3, a=4, b=5))"

    add_middleware(a.f, MyMiddleware("b"))
    assert a.f._middlewares[a] == [MyMiddleware("a"), MyMiddleware("b")]  # type: ignore[attr-defined]
    assert a.f(1, 2, 3, a=4, b=5) == "a.call(b.call(f(1, 2, 3, a=4, b=5)))"

    add_middleware(a.f, MyMiddleware("c"))
    assert a.f._middlewares[a] == [MyMiddleware("a"), MyMiddleware("b"), MyMiddleware("c")]  # type: ignore[attr-defined]
    assert a.f(1, 2, 3, a=4, b=5) == "a.call(b.call(c.call(f(1, 2, 3, a=4, b=5))))"

    add_middleware(a.f, MyMiddleware("A"), position=0)
    assert a.f._middlewares[a] == [  # type: ignore[attr-defined]
        MyMiddleware("A"),
        MyMiddleware("a"),
        MyMiddleware("b"),
        MyMiddleware("c"),
    ]
    assert a.f(1, 2, 3, a=4, b=5) == "A.call(a.call(b.call(c.call(f(1, 2, 3, a=4, b=5)))))"

    add_middleware(a.f, MyMiddleware("B"), position=2)
    assert a.f._middlewares[a] == [  # type: ignore[attr-defined]
        MyMiddleware("A"),
        MyMiddleware("a"),
        MyMiddleware("B"),
        MyMiddleware("b"),
        MyMiddleware("c"),
    ]
    assert a.f(1, 2, 3, a=4, b=5) == "A.call(a.call(B.call(b.call(c.call(f(1, 2, 3, a=4, b=5))))))"

    add_middleware(a.f, MyMiddleware("C"), position=-1)
    assert a.f._middlewares[a] == [  # type: ignore[attr-defined]
        MyMiddleware("A"),
        MyMiddleware("a"),
        MyMiddleware("B"),
        MyMiddleware("b"),
        MyMiddleware("C"),
        MyMiddleware("c"),
    ]
    assert a.f(1, 2, 3, a=4, b=5) == "A.call(a.call(B.call(b.call(C.call(c.call(f(1, 2, 3, a=4, b=5)))))))"

    add_middleware(a.f, MyMiddleware("D"), position=6)
    assert a.f._middlewares[a] == [  # type: ignore[attr-defined]
        MyMiddleware("A"),
        MyMiddleware("a"),
        MyMiddleware("B"),
        MyMiddleware("b"),
        MyMiddleware("C"),
        MyMiddleware("c"),
        MyMiddleware("D"),
    ]
    assert a.f(1, 2, 3, a=4, b=5) == "A.call(a.call(B.call(b.call(C.call(c.call(D.call(f(1, 2, 3, a=4, b=5))))))))"


# def test_integration() -> None:
#     class A:
#         def __init__(self, name: str) -> None:
#             self.name = name

#         @register_for_middleware
#         def process_message(self, msg: str, skip_middleware: Optional[bool] = None) -> str:
#             return f"{self.name}.process_message({msg=})"

#     assert hasattr(A.process_message, "_origin")
#     assert hasattr(A.process_message, "_chained_calls")

#     def is_bound_method(method: Callable[..., Any]) -> bool:
#         return hasattr(method, "__self__") and method.__self__ is not None

#     print(f"{is_bound_method(A.process_message)=}")
#     print(f"{is_bound_method(A(name='a').process_message)=}")

#     class MyMiddleware:
#         def __init__(self, name: str) -> None:
#             self.name = name

#         def call(self, *args: Any, next: Callable[..., Any], **kwargs: Any) -> str:
#             retval = next(*args, **kwargs)
#             return f"{self.name}.{format_function(self.call, retval)}"

#         def trigger(self, *args: Any, **kwargs: Any) -> bool:
#             return not ("skip_middleware" in kwargs and kwargs["skip_middleware"])

#     a = A("a")
#     mw = MyMiddleware("mw")

#     assert a.process_message("hello") == "a.process_message(msg='hello')"

#     add_middleware(a.process_message, mw)

#     h: MiddlewareCallable = a.process_message  # type: ignore[assignment]
#     assert hasattr(h, "_origin")
#     assert hasattr(h, "_chained_calls")
#     assert isinstance(h._chained_calls, dict)
#     assert a in h._chained_calls.keys()
#     assert hasattr(h._chained_calls[a], "__call__")

#     actual = a.process_message("hello")
#     expected = "mw.call(a.process_message(msg='hello'))"
#     assert actual == expected, actual

#     assert h._middlewares[a] == [mw]  # type: ignore[comparison-overlap]

#     mw2 = MyMiddleware("mw2")
#     add_middleware(a.process_message, mw2)
#     actual = a.process_message("hello")
#     expected = "mw.call(mw2.call(a.process_message(msg='hello')))"
#     assert actual == expected, actual

#     b = A("b")
#     with pytest.raises(ValueError):
#         add_middleware(b.process_message, mw)

#     mwb = MyMiddleware("mwb")
#     add_middleware(b.process_message, mwb)

#     actual = b.process_message("hello")
#     expected = "mwb.call(b.process_message(msg='hello'))"
#     assert actual == expected, actual

#     actual = a.process_message("hello")
#     expected = "mw.call(mw2.call(a.process_message(msg='hello')))"
#     assert actual == expected, actual


# def test_example() -> None:
#     class A:
#         def __init__(self, name: str) -> None:
#             self.name = name

#         @register_for_middleware
#         def process_message(self, msg: str, skip_middleware: Optional[bool] = None) -> str:
#             return f"{self.name}.process_message({msg=})"

#     class MyMiddleware:
#         def __init__(self, name: str) -> None:
#             self.name = name

#         def call(self, *args: Any, next: Callable[..., Any], **kwargs: Any) -> str:
#             retval = next(*args, **kwargs)
#             return f"{self.name}.{format_function(self.call, retval)}"

#         def trigger(self, *args: Any, **kwargs: Any) -> bool:
#             return not ("skip_middleware" in kwargs and kwargs["skip_middleware"])

#     a = A("a")
#     add_middleware(a.process_message, MyMiddleware("mw"))

#     assert a.process_message("hello") == "mw.call(a.process_message(msg='hello'))"
#     assert a.process_message("hello", skip_middleware=False) == "mw.call(a.process_message(msg='hello'))"
#     assert a.process_message("hello", skip_middleware=True) == "a.process_message(msg='hello')"

#     add_middleware(a.process_message, MyMiddleware("MW"))
#     assert a.process_message("hello") == "mw.call(MW.call(a.process_message(msg='hello')))"
