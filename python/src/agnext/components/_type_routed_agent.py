import logging
from functools import wraps
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Literal,
    NoReturn,
    Protocol,
    Sequence,
    Type,
    TypeVar,
    cast,
    get_type_hints,
    overload,
    runtime_checkable,
)

from ..core import MESSAGE_TYPE_REGISTRY, BaseAgent, MessageContext
from ..core.exceptions import CantHandleException
from ._type_helpers import AnyType, get_types

logger = logging.getLogger("agnext")

ReceivesT = TypeVar("ReceivesT", contravariant=True)
ProducesT = TypeVar("ProducesT", covariant=True)

# TODO: Generic typevar bound binding U to agent type
# Can't do because python doesnt support it


@runtime_checkable
class MessageHandler(Protocol[ReceivesT, ProducesT]):
    target_types: Sequence[type]
    produces_types: Sequence[type]
    is_message_handler: Literal[True]

    async def __call__(self, message: ReceivesT, ctx: MessageContext) -> ProducesT: ...


# NOTE: this works on concrete types and not inheritance
# TODO: Use a protocl for the outer function to check checked arg names


@overload
def message_handler(
    func: Callable[[Any, ReceivesT, MessageContext], Coroutine[Any, Any, ProducesT]],
) -> MessageHandler[ReceivesT, ProducesT]: ...


@overload
def message_handler(
    func: None = None,
    *,
    strict: bool = ...,
) -> Callable[
    [Callable[[Any, ReceivesT, MessageContext], Coroutine[Any, Any, ProducesT]]],
    MessageHandler[ReceivesT, ProducesT],
]: ...


def message_handler(
    func: None | Callable[[Any, ReceivesT, MessageContext], Coroutine[Any, Any, ProducesT]] = None,
    *,
    strict: bool = True,
) -> (
    Callable[
        [Callable[[Any, ReceivesT, MessageContext], Coroutine[Any, Any, ProducesT]]],
        MessageHandler[ReceivesT, ProducesT],
    ]
    | MessageHandler[ReceivesT, ProducesT]
):
    def decorator(
        func: Callable[[Any, ReceivesT, MessageContext], Coroutine[Any, Any, ProducesT]],
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

        # print(type_hints)
        return_types = get_types(type_hints["return"])

        if return_types is None:
            raise AssertionError("Return type not found")

        # Convert target_types to list and stash

        @wraps(func)
        async def wrapper(self: Any, message: ReceivesT, ctx: MessageContext) -> ProducesT:
            if type(message) not in target_types:
                if strict:
                    raise CantHandleException(f"Message type {type(message)} not in target types {target_types}")
                else:
                    logger.warning(f"Message type {type(message)} not in target types {target_types}")

            return_value = await func(self, message, ctx)

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

    if func is None and not callable(func):
        return decorator
    elif callable(func):
        return decorator(func)
    else:
        raise ValueError("Invalid arguments")


class TypeRoutedAgent(BaseAgent):
    def __init__(self, description: str) -> None:
        # Self is already bound to the handlers
        self._handlers: Dict[
            Type[Any],
            Callable[[Any, MessageContext], Coroutine[Any, Any, Any | None]],
        ] = {}

        for attr in dir(self):
            if callable(getattr(self, attr, None)):
                handler = getattr(self, attr)
                if hasattr(handler, "is_message_handler"):
                    message_handler = cast(MessageHandler[Any, Any], handler)
                    for target_type in message_handler.target_types:
                        self._handlers[target_type] = message_handler
        subscriptions = list(self._handlers.keys())
        for message_type in self._handlers.keys():
            if not MESSAGE_TYPE_REGISTRY.is_registered(MESSAGE_TYPE_REGISTRY.type_name(message_type)):
                MESSAGE_TYPE_REGISTRY.add_type(message_type)
        subscriptions_str = [MESSAGE_TYPE_REGISTRY.type_name(message_type) for message_type in subscriptions]
        super().__init__(description, subscriptions_str)

    async def on_message(self, message: Any, ctx: MessageContext) -> Any | None:
        key_type: Type[Any] = type(message)  # type: ignore
        handler = self._handlers.get(key_type)  # type: ignore
        if handler is not None:
            return await handler(message, ctx)
        else:
            return await self.on_unhandled_message(message, ctx)

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> NoReturn:
        raise CantHandleException(f"Unhandled message: {message}")
