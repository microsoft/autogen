import inspect
from functools import wraps
import textwrap
from typing import Any, Callable, Dict, List, Optional, Protocol

from typing_extensions import TypeVar

from ..asyncio_utils import match_caller_type

__all__ = ["Middleware", "MiddlewareCallable", "add_middleware", "register_for_middleware", "set_middlewares"]

F = TypeVar("F", bound=Callable[..., Any])
H = TypeVar("H", bound=Callable[..., Any])
T = TypeVar("T")


class Middleware(Protocol):
    def call(self, *args: Any, **kwargs: Any) -> Any:
        """The function to called in the middleware chain."""
        ...  # pragma: no cover

    @property
    def _h(self) -> "MiddlewareCallable":
        """The hookable function to which the middleware is attached."""
        ...  # pragma: no cover


class MiddlewareCallable(Protocol):
    """Protocol for a function registered for middleware."""

    @property
    def _origin(self) -> Callable[..., Any]:
        ...  # pragma: no cover

    @property
    def _chained_call(self) -> Dict[Any, Callable[..., Any]]:
        ...  # pragma: no cover

    @property
    def _is_async(self) -> bool:
        ...  # pragma: no cover

    @property
    def _is_method(self) -> bool:
        ...  # pragma: no cover

    @property
    def _middlewares(self) -> Dict[Any, List[Middleware]]:
        ...  # pragma: no cover

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...  # pragma: no cover


def register_for_middleware(f: F) -> F:
    """Decorator to register a function for middleware.

    After being applied to a function, middlewares can be attached to it using `add_middleware` and
    `set_middlewares` methods.

    Args:
        f: The function to register.

    Returns:
        A function that is registered for middleware.
    """

    @wraps(f)
    def h_sync(*args: Any, **kwargs: Any) -> Any:
        # self is the first argument if the function is a method
        self = args[0]

        h: MiddlewareCallable = h_sync  # type: ignore[assignment]
        if self in h._chained_call:
            return h._chained_call[self](*args, **kwargs)  # type: ignore[attr-defined]
        else:
            return h._origin(*args, **kwargs)  # type: ignore[attr-defined]

    @wraps(f)
    async def h_async(*args: Any, **kwargs: Any) -> Any:
        # self is the first argument if the function is a method

        self = args[0]

        h: MiddlewareCallable = h_async  # type: ignore[assignment]
        if self in h._chained_call:
            return await h._chained_call[self](*args, **kwargs)  # type: ignore[attr-defined]
        else:
            return await h._origin(*args, **kwargs)  # type: ignore[attr-defined]

    # this is to reduce number of mypy errors below, although we don't care about errors here
    h: MiddlewareCallable = h_async if inspect.iscoroutinefunction(f) else h_sync  # type: ignore[assignment]

    h._origin = f  # type: ignore[misc]
    h._chained_call = dict()  # type: ignore[misc]

    # if the name of the first argument is `self` or `cls`, then we assume
    # this is a method, otherwise it is a function
    sig = inspect.signature(f)
    first_param_name = list(sig.parameters.keys())[0]
    h._is_method = first_param_name in ("self", "cls")  # type: ignore[misc]

    # if async, then we need to await the result
    h._is_async = inspect.iscoroutinefunction(f)  # type: ignore[misc]

    h._middlewares = {}  # type: ignore[misc]

    return h  # type: ignore[return-value]


def _get_next_function(h: MiddlewareCallable, mw: Middleware, next: Callable[..., Any]) -> Callable[..., Any]:
    next = match_caller_type(callee=next, caller=mw.call)
    call = match_caller_type(callee=mw.call, caller=h._origin)
    trigger = match_caller_type(callee=mw.trigger, caller=h._origin) if hasattr(mw, "trigger") else None

    if inspect.iscoroutinefunction(h._origin):

        async def _aa() -> None:
            pass  # pragma: no cover

        next_async = match_caller_type(callee=next, caller=_aa)

        @wraps(call)
        async def _chain_async(*args: Any, **kwargs: Any) -> Any:
            trigger_value = (await trigger(*args, **kwargs)) if trigger is not None else True
            if trigger_value:
                return await call(*args, next=next, **kwargs)
            else:
                return await next_async(*args, **kwargs)

        return _chain_async
    else:

        def _ss() -> None:
            pass  # pragma: no cover

        next_sync = match_caller_type(callee=next, caller=_ss)

        @wraps(call)
        def _chain_sync(*args: Any, **kwargs: Any) -> Any:
            if trigger is None or trigger(*args, **kwargs):
                return call(*args, next=next, **kwargs)
            else:
                return next_sync(*args, **kwargs)

        return _chain_sync


def _is_bound_method(method: Callable[..., Any]) -> bool:
    return hasattr(method, "__self__") and method.__self__ is not None


def _get_self_from_bounded(h: Callable[..., Any], *, self: Any = None) -> Any:
    if hasattr(h, "__self__") and h.__self__ is not None:
        return h.__self__
    else:
        raise ValueError(f"Functions {h} is not bounded.")  # pragma: no cover


def _build_middleware_chain(h: MiddlewareCallable) -> None:
    if not _is_bound_method(h):
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

    next = h._origin
    self = _get_self_from_bounded(h)

    for mw in reversed(h._middlewares[self]):
        next = _get_next_function(h, mw, next)
        mw._chained_call = next  # type: ignore[attr-defined]

    h._chained_call[self] = next  # type: ignore[misc]


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

    self = _get_self_from_bounded(h, self=None)
    if self not in _h._middlewares:
        _h._middlewares[self] = []

    if position is None:
        _h._middlewares[self].append(mw)
    else:
        _h._middlewares[self].insert(position, mw)

    mw._h = _h

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
        mw._h = _h

    self = _get_self_from_bounded(h, self=mw)
    if self not in _h._middlewares:
        _h._middlewares[self] = []

    _h._middlewares[self] = mws  # type: ignore[misc]

    _build_middleware_chain(_h)
