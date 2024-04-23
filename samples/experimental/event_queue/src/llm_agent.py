import asyncio
import datetime
import os
from dataclasses import dataclass
from typing import Dict, List

from openai import AsyncOpenAI

from .agent import Agent
from .events import Event, Message, NewMessageEvent, on


@dataclass
class OAITextMessage:
    role: str
    content: str

    def to_dict(self):
        return {"role": self.role, "content": self.content}


class LLMAgent(Agent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client: AsyncOpenAI = None
        self._history: Dict[str, List[OAITextMessage]] = {}

    def initialize(self):
        self._client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", None))

    def _save_message_to_history(self, msg: Message):
        role = "assistant" if msg.source == self.name else "user"
        oai_msg = OAITextMessage(role=role, content=msg.content)

        if msg.source not in self._history:
            self._history[msg.source] = []

        self._history[msg.source].append(oai_msg)

    @on(NewMessageEvent)
    async def handle_new_message(self, event: Event) -> None:

        if event.message.target != self.name:
            return

        if self._client is None:
            self.initialize()

        self._save_message_to_history(event.message)

        relevant_history = self._history[event.message.source]
        completion = await self._client.chat.completions.create(
            messages=[m.to_dict() for m in relevant_history],
            model="gpt-4-turbo",
        )

        response = completion.choices[0].message.content

        reply = NewMessageEvent(Message(source=self.name, target=event.message.source, content=response))

        await self.post_event(reply)
