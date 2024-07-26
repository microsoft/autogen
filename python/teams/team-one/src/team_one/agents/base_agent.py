from asyncio import Lock
from typing import List, Tuple

from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import (
    AssistantMessage,
    LLMMessage,
    UserMessage,
)
from agnext.core import CancellationToken

from team_one.messages import BroadcastMessage, RequestReplyMessage, ResetMessage, UserContent
from team_one.utils import message_content_to_str


class BaseAgent(TypeRoutedAgent):
    """An agent that handles the RequestReply and Broadcast messages"""

    def __init__(
        self,
        description: str,
        handle_messages_concurrently: bool = False,
    ) -> None:
        super().__init__(description)
        self._lock: Lock | None = None if handle_messages_concurrently else Lock()
        self._chat_history: List[LLMMessage] = []

    @message_handler
    async def handle_broadcast(self, message: BroadcastMessage, cancellation_token: CancellationToken) -> None:
        """Handle an incoming broadcast message."""
        assert isinstance(message.content, UserMessage)

        try:
            if self._lock is not None:
                await self._lock.acquire()

            self._chat_history.append(message.content)
        finally:
            if self._lock is not None:
                self._lock.release()

    @message_handler
    async def handle_reset(self, message: ResetMessage, cancellation_token: CancellationToken) -> None:
        """Handle a reset message."""
        try:
            if self._lock is not None:
                await self._lock.acquire()

            await self._reset(cancellation_token)
        finally:
            if self._lock is not None:
                self._lock.release()

    @message_handler
    async def handle_request_reply(self, message: RequestReplyMessage, cancellation_token: CancellationToken) -> None:
        """Respond to a reply request."""
        try:
            if self._lock is not None:
                await self._lock.acquire()

            request_halt, response = await self._generate_reply(cancellation_token)

            assistant_message = AssistantMessage(content=message_content_to_str(response), source=self.metadata["name"])
            self._chat_history.append(assistant_message)

            user_message = UserMessage(content=response, source=self.metadata["name"])
            await self.publish_message(BroadcastMessage(content=user_message, request_halt=request_halt))
        finally:
            if self._lock is not None:
                self._lock.release()

    async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, UserContent]:
        """Returns (request_halt, response_message)"""
        raise NotImplementedError()

    async def _reset(self, cancellation_token: CancellationToken) -> None:
        self._chat_history = []
