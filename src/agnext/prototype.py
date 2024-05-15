from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, List, Protocol, Sequence, Type

# Type based routing for event

# -metadata
# Receipt
# Request response
# Type/Kind


# DELIVERY RECEIPTS


# on event
# on event with receipt


class Event(Protocol):
    sender: str
    # reply_to: Optional[str]


# T must encompass all subscribed types for a given agent


class Agent(Protocol):
    @property
    def name(self) -> str: ...


class EventBasedAgent[T: Event](Agent):
    @property
    def subscriptions(self) -> Sequence[Type[T]]: ...

    async def on_event(self, event: T) -> None: ...

    # async def _send_event(self, event: T) -> None:
    #     ...

    # async def _broadcast_message(self, event: T) -> None:
    #     ...


# NOTE: this works on concrete types and not inheritance
def event_handler[T: Event](target_type: Type[T]):
    def decorator(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
        func._target_type = target_type  # type: ignore
        return func

    return decorator


class TypeRoutedAgent[T: Event](EventBasedAgent[T], ABC):
    def __init__(self, name: str, emit_event: Callable[[T], Awaitable[None]]) -> None:
        self._name = name
        self._handlers: Dict[Type[Any], Callable[[T], Awaitable[None]]] = {}
        self._emit_event = emit_event

        for attr in dir(self):
            if callable(getattr(self, attr)):
                handler = getattr(self, attr)
                if hasattr(handler, "_target_type"):
                    # TODO do i need to partially apply self?
                    self._handlers[handler._target_type] = handler

    @property
    def name(self) -> str:
        return self._name

    @property
    def subscriptions(self) -> Sequence[Type[T]]:
        return list(self._handlers.keys())

    async def emit_event(self, event: T) -> None:
        await self._emit_event(event)

    async def on_event(self, event: T) -> None:
        handler = self._handlers.get(type(event))
        if handler is not None:
            await handler(event)
        else:
            await self.on_unhandled_event(event)

    @abstractmethod
    async def on_unhandled_event(self, event: T) -> None: ...


class EventQueue[U]:
    def __init__(self) -> None:
        self._queue: List[U] = []

    async def emit(self, event: U) -> None:
        print(event)
        self._queue.append(event)

    def pop_event(self) -> U:
        return self._queue.pop(0)

    def empty(self) -> bool:
        return len(self._queue) == 0

    def into_callable(self) -> Callable[[U], Awaitable[None]]:
        return self.emit


class EventRouter[T: Event]:
    def __init__(self, event_queue: EventQueue[T], agents: Sequence[EventBasedAgent[T]]) -> None:
        self._event_queue = event_queue
        # Use default dict i just cant remember the syntax and im without internet
        self._per_type_subscribers: Dict[Type[T], List[EventBasedAgent[T]]] = {}
        for agent in agents:
            subscriptions = agent.subscriptions
            for subscription in subscriptions:
                if subscription not in self._per_type_subscribers:
                    self._per_type_subscribers[subscription] = []

                self._per_type_subscribers[subscription].append(agent)

    async def process_next(self) -> None:
        if self._event_queue.empty():
            return

        event = self._event_queue.pop_event()
        subscribers = self._per_type_subscribers.get(type(event))
        if subscribers is not None:
            for subscriber in subscribers:
                await subscriber.on_event(event)
        else:
            print(f"Event {event} has no recipient agent")
