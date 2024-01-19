import inspect
from functools import wraps
import textwrap
from typing import Any, Callable, Dict, List, Optional, Protocol

from typing_extensions import TypeVar

from ..asyncio_utils import match_caller_type

# __all__ = ["Middleware", "MiddlewareCallable", "add_middleware", "register_for_middleware", "set_middlewares"]
__all__ = ["Middleware", "MiddlewareCallable", "register_for_middleware"]

F = TypeVar("F", bound=Callable[..., Any])
H = TypeVar("H", bound=Callable[..., Any])
T = TypeVar("T")


class Middleware(Protocol):
    def call(self, *args: Any, **kwargs: Any) -> Any:
        """The function to called in the middleware chain."""
        ...  # pragma: no cover

    async def a_call(self, *args: Any, **kwargs: Any) -> Any:
        """The function to awaited in the middleware chain."""
        ...  # pragma: no cover

    @property
    def _bound_h(self) -> "MiddlewareCallable":
        """The bound function to which the middleware is attached.

        Could be either async or sync
        """
        ...  # pragma: no cover


class MiddlewareCallable(Protocol):
    """Protocol for a function registered for middleware."""

    @property
    def _origin(self) -> Callable[..., Any]:
        ...  # pragma: no cover

    @property
    def _chained_calls(self) -> Dict[Any, Callable[..., Any]]:
        ...  # pragma: no cover

    @property
    def _is_async(self) -> bool:
        ...  # pragma: no cover

    @property
    def _middlewares(self) -> Dict[Any, List[Middleware]]:
        ...  # pragma: no cover

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...  # pragma: no cover


def _is_bound_to_instance_method(method: Callable[..., Any]) -> bool:
    return hasattr(method, "__self__") and (method.__self__ is not None) and (not inspect.isclass(method.__self__))


def _is_instance_method(f: Callable[..., Any]) -> bool:
    try:
        sig = inspect.signature(f)
        first_param_name = list(sig.parameters.keys())[0]
        return first_param_name == "self"
    except Exception:
        return False


def register_for_middleware(f: F) -> F:
    """Decorator to register a function for middleware.

    After being applied to a function, middlewares can be attached to it using `add_middleware` and
    `set_middlewares` methods.

    Args:
        f: The function to register.

    Returns:
        A function that is registered for middleware.

    Raises:
        ValueError: If the function is not an instance method.
    """

    if not _is_instance_method(f):
        msg = """\
        Only instance methods can be registered for middleware.

        Example:
            class A():
                @register_for_middleware
                def f(self):
                    pass

            # raises ValueError
            class B():
                @register_for_middleware
                @classmethod
                def f(cls):
                    pass
        """
        raise ValueError(textwrap.dedent(msg))

    if not inspect.iscoroutinefunction(f):

        @wraps(f)
        def h_sync(*args: Any, **kwargs: Any) -> Any:
            self = args[0]

            h: MiddlewareCallable = h_sync  # type: ignore[assignment]
            if self in h._chained_calls:
                args = args[1:]
                return h._chained_calls[self](*args, **kwargs)
            else:
                return h._origin(*args, **kwargs)

        h: MiddlewareCallable = h_sync  # type: ignore[assignment]
    else:

        @wraps(f)
        async def h_async(*args: Any, **kwargs: Any) -> Any:
            self = args[0]

            h: MiddlewareCallable = h_async  # type: ignore[assignment]
            if self in h._chained_calls:
                args = args[1:]
                return await h._chained_calls[self](*args, **kwargs)
            else:
                return await h._origin(*args, **kwargs)

        h = h_async  # type: ignore[assignment]

    h._origin = f  # type: ignore[misc]
    h._chained_calls = {}  # type: ignore[misc]
    h._is_async = inspect.iscoroutinefunction(f)  # type: ignore[misc]

    h._middlewares = {}  # type: ignore[misc]

    return h  # type: ignore[return-value]


def _get_self_from_bound(h: Callable[..., Any], *, self: Any = None) -> Any:
    if hasattr(h, "__self__") and h.__self__ is not None:
        return h.__self__
    else:
        raise ValueError(f"Functions {h} is not bound.")  # pragma: no cover


# inductive base
def _next_function_base(mw: Middleware) -> Callable[..., Any]:
    f = mw._bound_h
    self = _get_self_from_bound(f)
    return f._origin.__get__(self)  # type: ignore[no-any-return]


# inductive step
def _next_function_step(mw: Middleware, next: Callable[..., Any]) -> Callable[..., Any]:
    if inspect.iscoroutinefunction(next):

        @wraps(next)
        async def _next_async(*args: Any, **kwargs: Any) -> Any:
            return await mw.a_call(*args, next=next, **kwargs)

        return _next_async
    else:

        @wraps(next)
        def _next_sync(*args: Any, **kwargs: Any) -> Any:
            return mw.call(*args, next=next, **kwargs)

        return _next_sync


def _build_middleware_chain(h: MiddlewareCallable) -> None:
    if not _is_bound_to_instance_method(h):
        msg = """\
        Middleware can only be added to bound methods.

        Example:
            class A():
                @register_for_middleware
                def f(self):
                    pass

            class Middleware():
                def call(self, *args, **kwargs):
                    pass

            a = A()
            mw = Middleware()
            add_middleware(a.f, mw)

            # raises ValueError
            add_middleware(A.f, mw)
        """
        raise ValueError(textwrap.dedent(msg))

    self = _get_self_from_bound(h)
    mwx = h._middlewares[self] if self in h._middlewares else []

    if mwx:
        next = _next_function_base(mwx[0])

        for mw in reversed(mwx):
            next = _next_function_step(mw, next)

        h._chained_calls[self] = next
        # assert False
    else:
        if self in h._chained_calls:
            h._chained_calls.pop(self)


def _check_for_added_to_multiple_functions(h: MiddlewareCallable, mw: Middleware) -> None:
    msg = """\
    The same instance of the middleware cannot be added to multiple functions.

    Example:
        class A():
            @register_for_middleware
            def f(self):
                pass

        class Middleware():
            def call(self, *args, **kwargs):
                pass

        a = A()
        b = A()

        mwa = Middleware()
        mwb = Middleware()

        add_middleware(a.f, mwa)

        # raises ValueError
        add_middleware(b.f, mwa)
    """
    if hasattr(mw, "_h") and mw._h is not None and mw._h != h:
        raise ValueError(textwrap.dedent(msg))


def add_middleware(h: Callable[..., Any], mw: Any, *, position: Optional[int] = None) -> None:
    """Add a middleware to a hookable function.

    Args:
        h: A function registered for middleware.
        mw: The middleware to add.
        position: The position to insert the middleware at. If `None`, then the middleware is appended to the end.
    """
    _h: MiddlewareCallable = h  # type: ignore[assignment]

    _check_for_added_to_multiple_functions(_h, mw)

    self = _get_self_from_bound(h, self=None)
    if self not in _h._middlewares:
        _h._middlewares[self] = []

    if position is None:
        _h._middlewares[self].append(mw)
    else:
        _h._middlewares[self].insert(position, mw)

    mw._bound_h = _h

    # we could update the chain in-place, but this is a more robust solution
    _build_middleware_chain(_h)


def set_middlewares(h: Callable[..., Any], mws: List[Any]) -> None:
    """Set the middlewares for a hookable function.

    Args:
        h: The hookable function.
        mws: The middlewares to set.

    Raises:
        TypeError: If any of the middlewares cannot be used with the hookable function due to hookable function `h`
            being sync and `mw.call`` being async function for any `mw in mws`.

    """
    _h: MiddlewareCallable = h  # type: ignore[assignment]

    for mw in mws:
        _check_for_added_to_multiple_functions(_h, mw)
        mw._bound_h = _h

    self = _get_self_from_bound(h, self=mw)
    if self not in _h._middlewares:
        _h._middlewares[self] = []

    _h._middlewares[self] = mws

    _build_middleware_chain(_h)
