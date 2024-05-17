from typing import Any, Awaitable, Callable, Dict, Sequence, Type, TypeVar

from agnext.core.agent_runtime import AgentRuntime
from agnext.core.base_agent import BaseAgent
from agnext.core.exceptions import CantHandleException

from ..core.message import Message

T = TypeVar("T", bound=Message)


# NOTE: this works on concrete types and not inheritance
def message_handler(target_type: Type[T]) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        func._target_type = target_type  # type: ignore
        return func

    return decorator


class TypeRoutedAgent(BaseAgent[T]):
    def __init__(self, name: str, router: AgentRuntime[T]) -> None:
        super().__init__(name, router)

        self._handlers: Dict[Type[Any], Callable[[T], Awaitable[T]]] = {}

        router.add_agent(self)

        for attr in dir(self):
            if callable(getattr(self, attr)):
                handler = getattr(self, attr)
                if hasattr(handler, "_target_type"):
                    # TODO do i need to partially apply self?
                    self._handlers[handler._target_type] = handler

    @property
    def subscriptions(self) -> Sequence[Type[T]]:
        return list(self._handlers.keys())

    async def on_message(self, message: T) -> T:
        handler = self._handlers.get(type(message))
        if handler is not None:
            return await handler(message)
        else:
            return await self.on_unhandled_message(message)

    async def on_unhandled_message(self, message: T) -> T:
        raise CantHandleException()
