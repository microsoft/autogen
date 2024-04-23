import asyncio
import functools
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Type


@dataclass
class Message:
    source: str
    target: str
    content: str


@dataclass
class Event:
    message: Message


class NewMessageEvent(Event):
    pass


class SafetyAssessment(Event):
    pass


class AsyncEventQueue:

    def __init__(self) -> None:
        self.subscribers: Dict[Type[Event], List[Callable[[Event], Any]]] = {}

    async def subscribe(self, event_class: Type[Event], handler: Callable[[Event], Any]) -> None:
        """Subscribe to an event class"""
        if event_class not in self.subscribers:
            self.subscribers[event_class] = []
        if handler not in self.subscribers[event_class]:
            self.subscribers[event_class].append(handler)
            # print("Appending ", handler)

    async def post(self, event: Event) -> None:
        """Post an event to the queue"""
        if type(event) in self.subscribers:
            await asyncio.gather(*(handler(event) for handler in self.subscribers[type(event)]))


default_queue = AsyncEventQueue()


def on(event_class: Type[Event]) -> Callable[[Callable[[Event], Any]], Callable[[Event], Any]]:
    def decorator(func: Callable[[Event], Any]) -> Callable[[Event], Any]:

        @functools.wraps(func)
        async def wrapper(self: Any, event: Event) -> Any:
            return await func(self, event)

        wrapper.event_class = event_class
        return wrapper

    return decorator
