"""Hookable functions and methods.
"""
from functools import wraps
import inspect
from typing import Any, Awaitable, Callable, List, Optional, Tuple, TypeVar, Protocol, Union

from .conditions import Condition

__all__ = ["Hookable", "hookable_method", "hookable_function", "await_if_needed"]

F = TypeVar("F", bound=Callable[..., Any])
H = TypeVar("H", bound=Callable[..., Any])
T = TypeVar("T")

ConditionalCallable = Tuple[Optional[Condition], Callable[..., Any]]


class Hookable(Protocol):
    """Protocol for hookable functions and methods."""

    @property
    def _pre_hooks(self) -> List[ConditionalCallable]:
        ...

    @property
    def _post_hooks(self) -> List[ConditionalCallable]:
        ...

    @property
    def _origin(self) -> Callable[..., Any]:
        ...

    def add_pre_hook(self, h: H) -> H:
        ...

    def add_post_hook(self, h: H) -> H:
        ...

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


def _add_pre_hook(f_with_hooks: Hookable, h: H, cond: Condition) -> H:
    if inspect.iscoroutinefunction(h) and not inspect.iscoroutinefunction(f_with_hooks):
        raise TypeError("Cannot attach async hook to sync function.")
    f_with_hooks._pre_hooks.append((cond, h))
    return h


def _add_post_hook(f_with_hooks: Hookable, h: H, cond: Condition) -> H:
    if inspect.iscoroutinefunction(h) and not inspect.iscoroutinefunction(f_with_hooks):
        raise TypeError("Cannot attach async hook to sync function.")
    f_with_hooks._post_hooks.append((cond, h))
    return h


async def await_if_needed(x: Any) -> Any:
    if inspect.isawaitable(x):
        return await x
    else:
        return x


def hookable_method(cond: Optional[Condition] = None) -> Callable[[F], Hookable]:
    """Decorator to mark a method as hookable.

    Args:
        f: The method marked to be hookable.

    Returns:
        The method with empty list of hooks and two methods `pre_hook` and `post_hook` to add hooks.

    Example:
        ```python
        from autogen.hooks import hookable_method

        class A:
            @hookable_method
            def f(self, x: float, y: float, *, z: int):
                return (x + y) * z

        a = A()

        # we can add hooks using decorators
        @a.f.add_pre_hook()
        def add_one(x: float, y: float, *, z: int):
            return x + 1

        def deduct_one(x: float, y: float, *, z: int):
            return x - 1

        # or we can add hooks using function calls
        a.f.add_post_hook()(deduct_one)

        assert a.f(1.1, 2.2, z=3) == (1.1 + 1 + 2.2) * 3 - 1
        ```
    """

    def _hookable_method(f: F) -> Hookable:
        print(f"_hookable_method({f=})")

        @wraps(f)
        def f_with_hooks_sync(self: Any, x: Any, *args: Any, **kwargs: Any) -> Any:
            print(f"f_with_hooks_sync({self=}, {x=}, {args=}, {kwargs=})")
            for c, pre_hook in f_with_hooks._pre_hooks:  # type: ignore [attr-defined]
                if c is None or c():
                    x = pre_hook(x, *args, **kwargs)
                    print(f" - {x=}")

            y = f(self, x, *args, **kwargs)

            for c, post_hook in f_with_hooks._post_hooks:  # type: ignore [attr-defined]
                if c is None or c():
                    y = post_hook(y, *args, **kwargs)
                    print(f" - {y=}")

            return y

        @wraps(f)
        async def f_with_hooks_async(self: Any, x: Any, *args: Any, **kwargs: Any) -> Any:
            print(f"f_with_hooks_async({self=}, {x=}, {args=}, {kwargs=})")
            for c, pre_hook in f_with_hooks._pre_hooks:  # type: ignore [attr-defined]
                if c is None or c():
                    print(f"calling pre_hook: {pre_hook}({x=}, {args=}, {kwargs=})")
                    x = pre_hook(x, *args, **kwargs)
                    print(f" - {x=}")
                    x = await await_if_needed(x)
                    print(f" - awaited {x=}")

            y = await f(self, x, *args, **kwargs)

            for c, post_hook in f_with_hooks._post_hooks:  # type: ignore [attr-defined]
                if c is None or c():
                    y = await await_if_needed(post_hook(y, *args, **kwargs))
                    print(f" - {y=}")

            return y

        f_with_hooks = f_with_hooks_async if inspect.iscoroutinefunction(f) else f_with_hooks_sync

        f_with_hooks._pre_hooks = []  # type: ignore [attr-defined]
        f_with_hooks._post_hooks = []  # type: ignore [attr-defined]

        f_with_hooks.add_pre_hook = lambda h: _add_pre_hook(f_with_hooks, h, cond)  # type: ignore [attr-defined,arg-type]
        f_with_hooks.add_post_hook = lambda h: _add_post_hook(f_with_hooks, h, cond)  # type: ignore [attr-defined,arg-type]
        f_with_hooks._origin = f  # type: ignore [attr-defined]

        return f_with_hooks  # type: ignore [return-value]

    return _hookable_method


def hookable_function(cond: Optional[Condition] = None) -> Callable[[F], Hookable]:
    """Decorator to mark a function as hookable.

    Args:
        f: The function marked to be hookable.

    Returns:
        The function with empty list of hooks and two methods `pre_hook` and `post_hook` to add hooks.

    Example:
        ```python
        from autogen.hooks import hookable_function

        @hookable_function()
        def g(x: float, y: float, *, z: int):
            return (x + y) * z

        # we can add hooks using decorators
        @g.add_pre_hook
        def add_one(x: float, y: float, *, z: int):
            return x + 1

        def deduct_one(x: float, y: float, *, z: int):
            return x - 1

        # or we can add hooks using function calls
        g.add_post_hook()(deduct_one)

        assert g(1.1, 2.2, z=3) == (1.1 + 1 + 2.2) * 3 - 1
    """

    def _hookable_function(f: F) -> Hookable:
        @wraps(f)
        def f_with_hooks_sync(x: Any, *args: Any, **kwargs: Any) -> Any:
            for c, pre_hook in f_with_hooks._pre_hooks:  # type: ignore [attr-defined]
                if c is None or c():
                    x = pre_hook(x, *args, **kwargs)
                    print(f" - {x=}")
            y = f(x, *args, **kwargs)
            for c, post_hook in f_with_hooks._post_hooks:  # type: ignore [attr-defined]
                if c is None or c():
                    y = post_hook(y, *args, **kwargs)
                    print(f" - {y=}")
            return y

        @wraps(f)
        async def f_with_hooks_async(x: Any, *args: Any, **kwargs: Any) -> Any:
            for c, pre_hook in f_with_hooks._pre_hooks:  # type: ignore [attr-defined]
                if c is None or c():
                    x = await await_if_needed(pre_hook(x, *args, **kwargs))
            y = await f(x, *args, **kwargs)
            for c, post_hook in f_with_hooks._post_hooks:  # type: ignore [attr-defined]
                if c is None or c():
                    y = await await_if_needed(post_hook(y, *args, **kwargs))
            return y

        f_with_hooks = f_with_hooks_async if inspect.iscoroutinefunction(f) else f_with_hooks_sync

        f_with_hooks._pre_hooks = []  # type: ignore [attr-defined]
        f_with_hooks._post_hooks = []  # type: ignore [attr-defined]

        f_with_hooks.add_pre_hook = lambda h: _add_pre_hook(f_with_hooks, h, cond)  # type: ignore [attr-defined,arg-type]
        f_with_hooks.add_post_hook = lambda h: _add_post_hook(f_with_hooks, h, cond)  # type: ignore [attr-defined,arg-type]
        f_with_hooks._origin = f  # type: ignore [attr-defined]

        return f_with_hooks  # type: ignore [return-value]

    return _hookable_function
