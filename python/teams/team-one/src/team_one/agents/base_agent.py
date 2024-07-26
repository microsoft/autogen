import logging
from asyncio import Lock
from typing import List, Tuple

from agnext.application.logging import EVENT_LOGGER_NAME
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import (
    AssistantMessage,
    LLMMessage,
    UserMessage,
)
from agnext.core import CancellationToken

from team_one.messages import (
    AgentEvent,
    BroadcastMessage,
    DeactivateMessage,
    RequestReplyMessage,
    ResetMessage,
    UserContent,
)
from team_one.utils import message_content_to_str

logger = logging.getLogger(EVENT_LOGGER_NAME + ".orchestrator")


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
        self._enabled: bool = True

    @message_handler
    async def handle_broadcast(self, message: BroadcastMessage, cancellation_token: CancellationToken) -> None:
        """Handle an incoming broadcast message."""
        if not self._enabled:
            return
        assert isinstance(message.content, UserMessage)

        try:
            if self._lock is not None:
                await self._lock.acquire()

            ### CRITICAL SECTION
            self._chat_history.append(message.content)
            ###

        finally:
            if self._lock is not None:
                self._lock.release()

    @message_handler
    async def handle_reset(self, message: ResetMessage, cancellation_token: CancellationToken) -> None:
        """Handle a reset message."""
        if not self._enabled:
            return

        try:
            if self._lock is not None:
                await self._lock.acquire()

            ### CRITICAL SECTION
            await self._reset(cancellation_token)
            ###

        finally:
            if self._lock is not None:
                self._lock.release()

    @message_handler
    async def handle_deactivate(self, message: DeactivateMessage, cancellation_token: CancellationToken) -> None:
        """Handle a deactivate message."""
        if not self._enabled:
            return

        try:
            if self._lock is not None:
                await self._lock.acquire()

            ### CRITICAL SECTION
            self._enabled = False
            logger.info(
                AgentEvent(
                    f"{self.metadata['name']} (deactivated)",
                    "",
                )
            )
            ###

        finally:
            if self._lock is not None:
                self._lock.release()

    @message_handler
    async def handle_request_reply(self, message: RequestReplyMessage, cancellation_token: CancellationToken) -> None:
        """Respond to a reply request."""
        if not self._enabled:
            return

        try:
            if self._lock is not None:
                await self._lock.acquire()

            ### CRITICAL SECTION
            request_halt, response = await self._generate_reply(cancellation_token)

            assistant_message = AssistantMessage(content=message_content_to_str(response), source=self.metadata["name"])
            self._chat_history.append(assistant_message)

            user_message = UserMessage(content=response, source=self.metadata["name"])
            await self.publish_message(BroadcastMessage(content=user_message, request_halt=request_halt))
            ###

        finally:
            if self._lock is not None:
                self._lock.release()

    async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, UserContent]:
        """Returns (request_halt, response_message)"""
        raise NotImplementedError()

    async def _reset(self, cancellation_token: CancellationToken) -> None:
        self._chat_history = []
