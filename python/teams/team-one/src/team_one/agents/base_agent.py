import asyncio
import logging
from typing import Any, List, Tuple

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


PossibleMessages = RequestReplyMessage | BroadcastMessage | ResetMessage | DeactivateMessage


class BaseAgent(TypeRoutedAgent):
    """An agent that handles the RequestReply and Broadcast messages"""

    def __init__(
        self,
        description: str,
        handle_messages_concurrently: bool = False,
    ) -> None:
        super().__init__(description)
        self._chat_history: List[LLMMessage] = []
        self._enabled: bool = True

        self._handle_messages_concurrently = handle_messages_concurrently

        if not self._handle_messages_concurrently:
            # TODO: make it possible to stop
            self._message_queue = asyncio.Queue[tuple[PossibleMessages, CancellationToken, asyncio.Future[Any]]]()
            self._processing_task = asyncio.create_task(self._process())

    async def _process(self) -> None:
        while True:
            message, cancellation_token, future = await self._message_queue.get()
            if cancellation_token.is_cancelled():
                # TODO: Do we need to resolve the future here?
                continue

            if isinstance(message, RequestReplyMessage):
                await self.handle_request_reply(message, cancellation_token)
            elif isinstance(message, BroadcastMessage):
                await self.handle_broadcast(message, cancellation_token)
            elif isinstance(message, ResetMessage):
                await self.handle_reset(message, cancellation_token)
            elif isinstance(message, DeactivateMessage):
                await self.handle_deactivate(message, cancellation_token)
            else:
                raise ValueError("Unknown message type.")

            future.set_result(None)

    @message_handler
    async def handle_incoming_message(
        self,
        message: BroadcastMessage | ResetMessage | DeactivateMessage | RequestReplyMessage,
        cancellation_token: CancellationToken,
    ) -> None:
        if not self._enabled:
            return

        if self._handle_messages_concurrently:
            if isinstance(message, RequestReplyMessage):
                await self.handle_request_reply(message, cancellation_token)
            elif isinstance(message, BroadcastMessage):
                await self.handle_broadcast(message, cancellation_token)
            elif isinstance(message, ResetMessage):
                await self.handle_reset(message, cancellation_token)
            elif isinstance(message, DeactivateMessage):
                await self.handle_deactivate(message, cancellation_token)
        else:
            future = asyncio.Future[Any]()
            await self._message_queue.put((message, cancellation_token, future))
            await future

    async def handle_broadcast(self, message: BroadcastMessage, cancellation_token: CancellationToken) -> None:
        assert isinstance(message.content, UserMessage)
        self._chat_history.append(message.content)

    async def handle_reset(self, message: ResetMessage, cancellation_token: CancellationToken) -> None:
        """Handle a reset message."""
        await self._reset(cancellation_token)

    async def handle_deactivate(self, message: DeactivateMessage, cancellation_token: CancellationToken) -> None:
        """Handle a deactivate message."""
        self._enabled = False
        logger.info(
            AgentEvent(
                f"{self.metadata['name']} (deactivated)",
                "",
            )
        )

    async def handle_request_reply(self, message: RequestReplyMessage, cancellation_token: CancellationToken) -> None:
        """Respond to a reply request."""
        request_halt, response = await self._generate_reply(cancellation_token)

        assistant_message = AssistantMessage(content=message_content_to_str(response), source=self.metadata["name"])
        self._chat_history.append(assistant_message)

        user_message = UserMessage(content=response, source=self.metadata["name"])
        await self.publish_message(BroadcastMessage(content=user_message, request_halt=request_halt))

    async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, UserContent]:
        """Returns (request_halt, response_message)"""
        raise NotImplementedError()

    async def _reset(self, cancellation_token: CancellationToken) -> None:
        self._chat_history = []
