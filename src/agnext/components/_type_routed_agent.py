import logging
from functools import wraps
from types import NoneType, UnionType
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Literal,
    NoReturn,
    Optional,
    Protocol,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)

from ..core import AgentRuntime, BaseAgent, CancellationToken
from ..core.exceptions import CantHandleException

logger = logging.getLogger("agnext")

ReceivesT = TypeVar("ReceivesT", contravariant=True)
ProducesT = TypeVar("ProducesT", covariant=True)

# TODO: Generic typevar bound binding U to agent type
# Can't do because python doesnt support it


def is_union(t: object) -> bool:
    origin = get_origin(t)
    return origin is Union or origin is UnionType


def is_optional(t: object) -> bool:
    origin = get_origin(t)
    return origin is Optional


# Special type to avoid the 3.10 vs 3.11+ difference of typing._SpecialForm vs typing.Any
class AnyType:
    pass


def get_types(t: object) -> Sequence[Type[Any]] | None:
    if is_union(t):
        return get_args(t)
    elif is_optional(t):
        return tuple(list(get_args(t)) + [NoneType])
    elif t is Any:
        return (AnyType,)
    elif isinstance(t, type):
        return (t,)
    elif isinstance(t, NoneType):
        return (NoneType,)
    else:
        return None


@runtime_checkable
class MessageHandler(Protocol[ReceivesT, ProducesT]):
    target_types: Sequence[type]
    produces_types: Sequence[type]
    is_message_handler: Literal[True]

    async def __call__(self, message: ReceivesT, cancellation_token: CancellationToken) -> ProducesT: ...


# NOTE: this works on concrete types and not inheritance
# TODO: Use a protocl for the outer function to check checked arg names
def message_handler(
    strict: bool = True,
) -> Callable[
    [Callable[[Any, ReceivesT, CancellationToken], Coroutine[Any, Any, ProducesT]]],
    MessageHandler[ReceivesT, ProducesT],
]:
    def decorator(
        func: Callable[[Any, ReceivesT, CancellationToken], Coroutine[Any, Any, ProducesT]],
    ) -> MessageHandler[ReceivesT, ProducesT]:
        type_hints = get_type_hints(func)
        if "message" not in type_hints:
            raise AssertionError("message parameter not found in function signature")

        if "return" not in type_hints:
            raise AssertionError("return not found in function signature")

        # Get the type of the message parameter
        target_types = get_types(type_hints["message"])
        if target_types is None:
            raise AssertionError("Message type not found")

        print(type_hints)
        return_types = get_types(type_hints["return"])

        if return_types is None:
            raise AssertionError("Return type not found")

        # Convert target_types to list and stash

        @wraps(func)
        async def wrapper(self: Any, message: ReceivesT, cancellation_token: CancellationToken) -> ProducesT:
            if type(message) not in target_types:
                if strict:
                    raise CantHandleException(f"Message type {type(message)} not in target types {target_types}")
                else:
                    logger.warning(f"Message type {type(message)} not in target types {target_types}")

            return_value = await func(self, message, cancellation_token)

            if AnyType not in return_types and type(return_value) not in return_types:
                if strict:
                    raise ValueError(f"Return type {type(return_value)} not in return types {return_types}")
                else:
                    logger.warning(f"Return type {type(return_value)} not in return types {return_types}")

            return return_value

        wrapper_handler = cast(MessageHandler[ReceivesT, ProducesT], wrapper)
        wrapper_handler.target_types = list(target_types)
        wrapper_handler.produces_types = list(return_types)
        wrapper_handler.is_message_handler = True

        return wrapper_handler

    return decorator


class TypeRoutedAgent(BaseAgent):
    def __init__(self, name: str, description: str, runtime: AgentRuntime) -> None:
        # Self is already bound to the handlers
        self._handlers: Dict[
            Type[Any],
            Callable[[Any, CancellationToken], Coroutine[Any, Any, Any | None]],
        ] = {}

        for attr in dir(self):
            if callable(getattr(self, attr, None)):
                handler = getattr(self, attr)
                if hasattr(handler, "is_message_handler"):
                    message_handler = cast(MessageHandler[Any, Any], handler)
                    for target_type in message_handler.target_types:
                        self._handlers[target_type] = message_handler

        super().__init__(name, description, runtime)

    @property
    def subscriptions(self) -> Sequence[Type[Any]]:
        return list(self._handlers.keys())

    async def on_message(self, message: Any, cancellation_token: CancellationToken) -> Any | None:
        key_type: Type[Any] = type(message)  # type: ignore
        handler = self._handlers.get(key_type)  # type: ignore
        if handler is not None:
            return await handler(message, cancellation_token)
        else:
            return await self.on_unhandled_message(message, cancellation_token)

    async def on_unhandled_message(self, message: Any, cancellation_token: CancellationToken) -> NoReturn:
        raise CantHandleException(f"Unhandled message: {message}")
