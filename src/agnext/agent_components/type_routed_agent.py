from typing import Any, Callable, Coroutine, Dict, NoReturn, Sequence, Type, TypeVar

from agnext.core.agent_runtime import AgentRuntime
from agnext.core.base_agent import BaseAgent
from agnext.core.cancellation_token import CancellationToken
from agnext.core.exceptions import CantHandleException

ReceivesT = TypeVar("ReceivesT")
ProducesT = TypeVar("ProducesT", covariant=True)

# TODO: Generic typevar bound binding U to agent type
# Can't do because python doesnt support it


# NOTE: this works on concrete types and not inheritance
def message_handler(
    *target_types: Type[ReceivesT],
) -> Callable[
    [Callable[[Any, ReceivesT, CancellationToken], Coroutine[Any, Any, ProducesT | None]]],
    Callable[[Any, ReceivesT, CancellationToken], Coroutine[Any, Any, ProducesT | None]],
]:
    def decorator(
        func: Callable[[Any, ReceivesT, CancellationToken], Coroutine[Any, Any, ProducesT | None]],
    ) -> Callable[[Any, ReceivesT, CancellationToken], Coroutine[Any, Any, ProducesT | None]]:
        # Convert target_types to list and stash
        func._target_types = list(target_types)  # type: ignore
        return func

    return decorator


class TypeRoutedAgent(BaseAgent):
    def __init__(self, name: str, router: AgentRuntime) -> None:
        # Self is already bound to the handlers
        self._handlers: Dict[Type[Any], Callable[[Any, CancellationToken], Coroutine[Any, Any, Any | None]]] = {}

        for attr in dir(self):
            if callable(getattr(self, attr, None)):
                handler = getattr(self, attr)
                if hasattr(handler, "_target_types"):
                    for target_type in handler._target_types:
                        self._handlers[target_type] = handler

        super().__init__(name, router)

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
