import logging
import asyncio
from dataclasses import dataclass
from typing import Protocol, Callable, Awaitable

from ..database.database import ChatMessage


class AgentManager(Protocol):

    async def generate_response(
        self,
        in_message: ChatMessage,
        out_message: ChatMessage,
        update_callback: Callable[[str], Awaitable[None]],
    ) -> ChatMessage:
        pass


class ReversedAgents:

    async def generate_response(
        self,
        in_message: ChatMessage,
        out_message: ChatMessage,
        update_callback: Callable[[str], Awaitable[None]],
    ) -> ChatMessage:

        logger = logging.getLogger(__name__)
        update_callback("Thinking...")
        logger.info("Thinking...")

        await asyncio.sleep(3)

        update_callback("Starting to reverse the message...")
        logger.info("Starting to reverse the message...")

        await asyncio.sleep(3)

        out_message.content = in_message.content[::-1]
        out_message.role = "assistant"
        return out_message
