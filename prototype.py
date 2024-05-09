from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol, Sequence, Type, cast

import asyncio

from abc import ABC, abstractmethod

import random



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


# T must encompass all subscribed types for a given agent

class Agent(Protocol):
    @property
    def name(self) -> str:
        ...

class EventBasedAgent[T: Event](Agent):
    @property
    def subscriptions(self) -> Sequence[Type[T]]:
        ...

    async def on_event(self, event: T) -> None:
        ...

# NOTE: this works on concrete types and not inheritance
def event_handler[T: Event](target_type: Type[T]):
    def decorator(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
        func._target_type = target_type # type: ignore
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
    async def on_unhandled_event(self, event: T) -> None:
        ...

@dataclass
class InputEvent(Event):
    message: str
    sender: str

@dataclass
class NewEvent(Event):
    message: str
    sender: str
    recipient: str

@dataclass
class ResponseEvent(Event):
    message: Optional[str]
    sender: str

GroupChatEvents = InputEvent | NewEvent | ResponseEvent

class GroupChatManager(TypeRoutedAgent[GroupChatEvents]):
    def __init__(self, name: str, emit_event: Callable[[GroupChatEvents], Awaitable[None]], agents: Sequence[Agent]) -> None:
        super().__init__(name, emit_event)
        self._agents = agents
        self._current_speaker = 0
        self._events: List[GroupChatEvents] = []
        self._responses: List[ResponseEvent] = []


    @event_handler(InputEvent)
    async def on_input_event(self, event: InputEvent) -> None:
        # New group chat
        self._events.clear()

        recipient_agent = self._agents[self._current_speaker]
        self._current_speaker = (self._current_speaker + 1) % len(self._agents)

        new_event = NewEvent(message=event.message, sender=self.name, recipient=recipient_agent.name)
        self._events.append(event)
        await self.emit_event(new_event)

    @event_handler(ResponseEvent)
    async def on_group_chat_event(self, event: ResponseEvent) -> None:

        self._responses.append(event)

        # TODO: Handle termination and replying to original sender

        # Received response from all - proceeed
        if len(self._responses) == len(self._agents):
            recipient_agent = self._agents[self._current_speaker]
            self._current_speaker = (self._current_speaker + 1) % len(self._agents)

            responses_with_content = [x for x in self._responses if x.message is not None]
            if len(responses_with_content) != 1:
                raise ValueError("Can't handle anything other than 1 response right now.")

            new_event = NewEvent(message=cast(str, responses_with_content[0].message), sender=self.name, recipient=recipient_agent.name)
            self._events.append(new_event)
            self._responses.clear()
            await self.emit_event(new_event)

    async def on_unhandled_event(self, event: GroupChatEvents) -> None:
        raise ValueError("Unknown")


class Critic(TypeRoutedAgent[GroupChatEvents]):
    def __init__(self, name: str, emit_event: Callable[[GroupChatEvents], Awaitable[None]]) -> None:
        super().__init__(name, emit_event)

    @event_handler(NewEvent)
    async def on_new_event(self, event: NewEvent) -> None:
        if event.recipient == self.name:
            response = random.choice([" is a good idea", " is a bad idea"])
            await self.emit_event(ResponseEvent(event.message + response, sender=self.name))
        else:
            await self.emit_event(ResponseEvent(None, sender=self.name))

    async def on_unhandled_event(self, event: GroupChatEvents) -> None:
        raise ValueError("Unknown")

class Suggester(TypeRoutedAgent[GroupChatEvents]):
    def __init__(self, name: str, emit_event: Callable[[GroupChatEvents], Awaitable[None]]) -> None:
        super().__init__(name, emit_event)

    @event_handler(NewEvent)
    async def on_new_event(self, event: NewEvent) -> None:
        if event.recipient == self.name:
            response = random.choice(["Attach wheels to a laptop", "merge a banana and an apple", "Cheese but made with oats"])
            await self.emit_event(ResponseEvent(response, sender=self.name))
        else:
            await self.emit_event(ResponseEvent(None, sender=self.name))

    async def on_unhandled_event(self, event: GroupChatEvents) -> None:
        raise ValueError("Unknown")

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


class EventRouter[T: Event]():
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

async def main():
    event_queue = EventQueue[GroupChatEvents]()

    critic = Critic("Critic", event_queue.into_callable())
    suggester = Suggester("Suggester", event_queue.into_callable())
    group_chat_manager = GroupChatManager("Manager", event_queue.into_callable(), [critic, suggester])
    processor = EventRouter(event_queue, [critic, suggester, group_chat_manager])

    await event_queue.emit(InputEvent(message="Go", sender="external"))

    await processor.process_next()
    await processor.process_next()
    await processor.process_next()
    await processor.process_next()
    await processor.process_next()
    await processor.process_next()
    await processor.process_next()
    await processor.process_next()
    await processor.process_next()
    await processor.process_next()
    await processor.process_next()


if __name__ == "__main__":
    asyncio.run(main())
