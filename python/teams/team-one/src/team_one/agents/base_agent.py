import asyncio
import logging
from typing import Any

from agnext.application.logging import EVENT_LOGGER_NAME
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import CancellationToken

from team_one.messages import (
    AgentEvent,
    BroadcastMessage,
    DeactivateMessage,
    RequestReplyMessage,
    ResetMessage,
    TeamOneMessages,
)

logger = logging.getLogger(EVENT_LOGGER_NAME + ".agent")


class TeamOneBaseAgent(TypeRoutedAgent):
    """An agent that optionally ensures messages are handled non-concurrently in the order they arrive."""

    def __init__(
        self,
        description: str,
        handle_messages_concurrently: bool = False,
    ) -> None:
        super().__init__(description)
        self._handle_messages_concurrently = handle_messages_concurrently
        self._enabled = True

        if not self._handle_messages_concurrently:
            # TODO: make it possible to stop
            self._message_queue = asyncio.Queue[tuple[TeamOneMessages, CancellationToken, asyncio.Future[Any]]]()
            self._processing_task = asyncio.create_task(self._process())

    async def _process(self) -> None:
        while True:
            message, cancellation_token, future = await self._message_queue.get()
            if cancellation_token.is_cancelled():
                # TODO: Do we need to resolve the future here?
                continue

            try:
                if isinstance(message, RequestReplyMessage):
                    await self._handle_request_reply(message, cancellation_token)
                elif isinstance(message, BroadcastMessage):
                    await self._handle_broadcast(message, cancellation_token)
                elif isinstance(message, ResetMessage):
                    await self._handle_reset(message, cancellation_token)
                elif isinstance(message, DeactivateMessage):
                    await self._handle_deactivate(message, cancellation_token)
                else:
                    raise ValueError("Unknown message type.")
                future.set_result(None)
            except Exception as e:
                future.set_exception(e)

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
                await self._handle_request_reply(message, cancellation_token)
            elif isinstance(message, BroadcastMessage):
                await self._handle_broadcast(message, cancellation_token)
            elif isinstance(message, ResetMessage):
                await self._handle_reset(message, cancellation_token)
            elif isinstance(message, DeactivateMessage):
                await self._handle_deactivate(message, cancellation_token)
        else:
            future = asyncio.Future[Any]()
            await self._message_queue.put((message, cancellation_token, future))
            await future

    async def _handle_broadcast(self, message: BroadcastMessage, cancellation_token: CancellationToken) -> None:
        raise NotImplementedError()

    async def _handle_reset(self, message: ResetMessage, cancellation_token: CancellationToken) -> None:
        raise NotImplementedError()

    async def _handle_request_reply(self, message: RequestReplyMessage, cancellation_token: CancellationToken) -> None:
        raise NotImplementedError()

    async def _handle_deactivate(self, message: DeactivateMessage, cancellation_token: CancellationToken) -> None:
        """Handle a deactivate message."""
        self._enabled = False
        logger.info(
            AgentEvent(
                f"{self.metadata['type']} (deactivated)",
                "",
            )
        )
