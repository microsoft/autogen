import asyncio
import random
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional, Sequence, cast

from agnext.prototype import Agent, Event, EventQueue, EventRouter, TypeRoutedAgent, event_handler


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
    def __init__(
        self, name: str, emit_event: Callable[[GroupChatEvents], Awaitable[None]], agents: Sequence[Agent]
    ) -> None:
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

            new_event = NewEvent(
                message=cast(str, responses_with_content[0].message), sender=self.name, recipient=recipient_agent.name
            )
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
            response = random.choice(
                ["Attach wheels to a laptop", "merge a banana and an apple", "Cheese but made with oats"]
            )
            await self.emit_event(ResponseEvent(response, sender=self.name))
        else:
            await self.emit_event(ResponseEvent(None, sender=self.name))

    async def on_unhandled_event(self, event: GroupChatEvents) -> None:
        raise ValueError("Unknown")


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
