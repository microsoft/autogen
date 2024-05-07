from dataclasses import dataclass
from typing import Awaitable, Callable, List, Mapping, Protocol, Sequence

import asyncio
from enum import Enum

# Type based routing for events

class EventKind(Enum):
    INPUT = "input"
    GROUP_CHAT = "GROUP_CHAT"

@dataclass
class Event:
    recipient: str
    payload: str
    kind: EventKind
    sender: str
    request_reply: bool = False

class EventBasedAgent(Protocol):

    @property
    def name(self) -> str:
        ...

    async def on_event(self, event: Event) -> None:
        ...


class EventRoutingAgent(EventBasedAgent):

    def __init__(self, name: str, emit_event: Callable[[Event], None], handlers: Mapping[EventKind, Callable[[Event], Awaitable[None]]]) -> None:
        self._name = name
        self._emit_event = emit_event
        self._emit_event = emit_event
        self._handlers = handlers

    @property
    def name(self) -> str:
        return self._name

    async def on_event(self, event: Event) -> None:
        handler = self._handlers.get(event.kind)
        if handler is not None:
            await handler(event)
        else:
            print(f"No handler for event {event}")

class CapitilizationAgent(EventBasedAgent):
    def __init__(self, name: str, emit_event: Callable[[Event], None]) -> None:
        self._name = name
        self._emit_event = emit_event

    @property
    def name(self) -> str:
        return self._name

    async def on_event(self, event: Event) -> None:
        payload = event.payload
        capitalized_payload = payload.upper()
        self._emit_event(Event(recipient=event.sender, payload=capitalized_payload, kind=event.kind, sender=self._name))

class GroupChatManager(EventRoutingAgent):
    def __init__(self, name: str, emit_event: Callable[[Event], None], agents: Sequence[EventBasedAgent]) -> None:

        super().__init__(name, emit_event, {
            EventKind.INPUT: self.on_input_event,
            EventKind.GROUP_CHAT: self.on_group_chat_event
        })

        self._agents = agents
        self._current_speaker = 0
        self._events: List[Event] = []


    @property
    def name(self) -> str:
        return self._name

    def broadcast(self, event: Event, next_speaker: EventBasedAgent) -> None:
        for agent in self._agents:
            event.recipient = agent.name
            event.request_reply = agent == next_speaker
            self._emit_event(event)



    async def on_input_event(self, event: Event) -> None:
        # New group chat
        self._events.clear()

        recipient_agent = self._agents[self._current_speaker]
        self._current_speaker = (self._current_speaker + 1) % len(self._agents)
        event.sender = self._name
        self._events.append(event)
        self.broadcast(event, recipient_agent)

    async def on_group_chat_event(self, event: Event) -> None:
        # Handle termination and replying to original sender
        recipient_agent = self._agents[self._current_speaker]
        self._current_speaker = (self._current_speaker + 1) % len(self._agents)
        event.sender = self._name
        self._events.append(event)
        self.broadcast(event, recipient_agent)




class EventQueue:
    def __init__(self) -> None:
        self._queue: List[Event] = []

    def emit(self, event: Event) -> None:
        print(event)
        self._queue.append(event)

    def pop_event(self) -> Event:
        return self._queue.pop(0)

    def empty(self) -> bool:
        return len(self._queue) == 0

    def into_callable(self) -> Callable[[Event], None]:
        return self.emit


class EventQueueProcessor():
    def __init__(self, event_queue: EventQueue, agents: Sequence[EventBasedAgent]) -> None:
        self._event_queue = event_queue
        self._agent_map = {agent.name: agent for agent in agents}

    async def process_next(self) -> None:
        if self._event_queue.empty():
            return

        event = self._event_queue.pop_event()
        recipient = event.recipient
        if recipient in self._agent_map:
            agent = self._agent_map[recipient]
            await agent.on_event(event)
        else:
            print(f"Event {event} has no recipient agent")

async def main():
    event_queue = EventQueue()
    agents = [
        CapitilizationAgent("CapitilizationAgent", event_queue.into_callable())
    ]
    processor = EventQueueProcessor(event_queue, agents)

    event_queue.emit(Event(recipient="CapitilizationAgent", payload="hello", kind=EventKind.INPUT, sender="main"))

    await processor.process_next()


if __name__ == "__main__":
    asyncio.run(main())
