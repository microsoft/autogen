import asyncio
import datetime

import openai

from .agent import Agent
from .events import Event, Message, NewMessageEvent, on


class UserAgent(Agent):

    @on(NewMessageEvent)
    async def get_user_input(self, event: Event) -> None:

        if event.message.target != self.name:
            return

        user_input = input("Enter text: ")

        reply = NewMessageEvent(Message(source=self.name, target=event.message.source, content=user_input))
        await self.post_event(reply)
