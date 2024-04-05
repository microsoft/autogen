import asyncio
from typing import Protocol, List

from ..database.database import ChatMessage


class AgentManager(Protocol):

    async def generate_response(self, in_message: ChatMessage, out_message: ChatMessage) -> ChatMessage:
        pass


class ReversedAgents:

    async def generate_response(self, in_message: ChatMessage, out_message: ChatMessage) -> ChatMessage:

        await asyncio.sleep(3)

        out_message.content = in_message.content[::-1]
        out_message.role = "assistant"
        return out_message
