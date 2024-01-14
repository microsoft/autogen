"""Hookable functions and methods.
"""
from functools import wraps
from typing import Any, Callable, List, TypeVar, Protocol, Union

F = TypeVar("F", bound=Callable[..., Any])
H = TypeVar("H", bound=Callable[..., Any])


class Hookable(Protocol):
    """Protocol for hookable functions and methods."""

    @property
    def _pre_hooks(self) -> List[Callable[..., Any]]:
        ...

    @property
    def _post_hooks(self) -> List[Callable[..., Any]]:
        ...

    @property
    def _origin(self) -> Callable[..., Any]:
        ...

    def pre_hook(self, h: H) -> H:
        ...

    def post_hook(self, h: H) -> H:
        ...

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


def _pre_hook(f_with_hooks: Hookable, h: H) -> H:
    if h in f_with_hooks._pre_hooks:
        raise ValueError(f"Hook {h} is already registered.")

    f_with_hooks._pre_hooks.append(h)
    return h


def _post_hook(f_with_hooks: Hookable, h: H) -> H:
    if h in f_with_hooks._pre_hooks:
        raise ValueError(f"Hook '{h.__name__}' is already registered.")

    f_with_hooks._post_hooks.append(h)
    return h


def hookable_method(f: F) -> Hookable:
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
        @a.f.add_pre_hook
        def add_one(x: float, y: float, *, z: int):
            return x + 1

        def deduct_one(x: float, y: float, *, z: int):
            return x - 1

        # or we can add hooks using function calls
        a.f.add_post_hook(deduct_one)

        assert a.f(1.1, 2.2, z=3) == (1.1 + 1 + 2.2) * 3 - 1
        ```
    """

    @wraps(f)
    def f_with_hooks(self: Any, x: Any, *args: Any, **kwargs: Any) -> Any:
        for pre_hook in f_with_hooks._pre_hooks:  # type: ignore [attr-defined]
            x = pre_hook(x, *args, **kwargs)
        y = f(self, x, *args, **kwargs)
        for post_hook in f_with_hooks._post_hooks:  # type: ignore [attr-defined]
            y = post_hook(y, *args, **kwargs)
        return y

    f_with_hooks._pre_hooks = []  # type: ignore [attr-defined]
    f_with_hooks._post_hooks = []  # type: ignore [attr-defined]

    f_with_hooks.add_pre_hook = lambda h: _pre_hook(f_with_hooks, h)  # type: ignore [attr-defined,arg-type]
    f_with_hooks.add_post_hook = lambda h: _post_hook(f_with_hooks, h)  # type: ignore [attr-defined,arg-type]
    f_with_hooks._origin = f  # type: ignore [attr-defined]

    return f_with_hooks  # type: ignore [return-value]


def hookable_function(f: F) -> Hookable:
    """Decorator to mark a function as hookable.

    Args:
        f: The function marked to be hookable.

    Returns:
        The function with empty list of hooks and two methods `pre_hook` and `post_hook` to add hooks.

    Example:
        ```python
        from autogen.hooks import hookable_function

        @hookable_function
        def g(x: float, y: float, *, z: int):
            return (x + y) * z

        # we can add hooks using decorators
        @g.add_pre_hook
        def add_one(x: float, y: float, *, z: int):
            return x + 1

        def deduct_one(x: float, y: float, *, z: int):
            return x - 1

        # or we can add hooks using function calls
        g.add_post_hook(deduct_one)

        assert g(1.1, 2.2, z=3) == (1.1 + 1 + 2.2) * 3 - 1
    """

    @wraps(f)
    def f_with_hooks(x: Any, *args: Any, **kwargs: Any) -> Any:
        for pre_hook in f_with_hooks._pre_hooks:  # type: ignore [attr-defined]
            x = pre_hook(x, *args, **kwargs)
        y = f(x, *args, **kwargs)
        for post_hook in f_with_hooks._post_hooks:  # type: ignore [attr-defined]
            y = post_hook(y, *args, **kwargs)
        return y

    f_with_hooks._pre_hooks = []  # type: ignore [attr-defined]
    f_with_hooks._post_hooks = []  # type: ignore [attr-defined]

    f_with_hooks.add_pre_hook = lambda h: _pre_hook(f_with_hooks, h)  # type: ignore [attr-defined,arg-type]
    f_with_hooks.add_post_hook = lambda h: _post_hook(f_with_hooks, h)  # type: ignore [attr-defined,arg-type]
    f_with_hooks._origin = f  # type: ignore [attr-defined]

    return f_with_hooks  # type: ignore [return-value]
