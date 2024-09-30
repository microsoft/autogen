import asyncio
import logging
from typing import Any

from autogen_core.application.logging import EVENT_LOGGER_NAME
from autogen_core.base import MessageContext
from autogen_core.components import RoutedAgent, message_handler

from team_one.messages import (
    AgentEvent,
    BroadcastMessage,
    DeactivateMessage,
    RequestReplyMessage,
    ResetMessage,
    TeamOneMessages,
)


class TeamOneBaseAgent(RoutedAgent):
    """An agent that optionally ensures messages are handled non-concurrently in the order they arrive."""

    def __init__(
        self,
        description: str,
        handle_messages_concurrently: bool = False,
    ) -> None:
        super().__init__(description)
        self._handle_messages_concurrently = handle_messages_concurrently
        self._enabled = True
        self.logger = logging.getLogger(EVENT_LOGGER_NAME + f".{self.id.key}.agent")

        if not self._handle_messages_concurrently:
            # TODO: make it possible to stop
            self._message_queue = asyncio.Queue[tuple[TeamOneMessages, MessageContext, asyncio.Future[Any]]]()
            self._processing_task = asyncio.create_task(self._process())

    async def _process(self) -> None:
        while True:
            message, ctx, future = await self._message_queue.get()
            if ctx.cancellation_token.is_cancelled():
                # TODO: Do we need to resolve the future here?
                future.cancel()
                continue

            try:
                if isinstance(message, RequestReplyMessage):
                    await self._handle_request_reply(message, ctx)
                elif isinstance(message, BroadcastMessage):
                    await self._handle_broadcast(message, ctx)
                elif isinstance(message, ResetMessage):
                    await self._handle_reset(message, ctx)
                elif isinstance(message, DeactivateMessage):
                    await self._handle_deactivate(message, ctx)
                else:
                    raise ValueError("Unknown message type.")
                future.set_result(None)
            except asyncio.CancelledError:
                future.cancel()
            except Exception as e:
                future.set_exception(e)

    @message_handler
    async def handle_incoming_message(
        self,
        message: BroadcastMessage | ResetMessage | DeactivateMessage | RequestReplyMessage,
        ctx: MessageContext,
    ) -> None:
        if not self._enabled:
            return

        if self._handle_messages_concurrently:
            if isinstance(message, RequestReplyMessage):
                await self._handle_request_reply(message, ctx)
            elif isinstance(message, BroadcastMessage):
                await self._handle_broadcast(message, ctx)
            elif isinstance(message, ResetMessage):
                await self._handle_reset(message, ctx)
            elif isinstance(message, DeactivateMessage):
                await self._handle_deactivate(message, ctx)
        else:
            future = asyncio.Future[Any]()
            await self._message_queue.put((message, ctx, future))
            await future

    async def _handle_broadcast(self, message: BroadcastMessage, ctx: MessageContext) -> None:
        raise NotImplementedError()

    async def _handle_reset(self, message: ResetMessage, ctx: MessageContext) -> None:
        raise NotImplementedError()

    async def _handle_request_reply(self, message: RequestReplyMessage, ctx: MessageContext) -> None:
        raise NotImplementedError()

    async def _handle_deactivate(self, message: DeactivateMessage, ctx: MessageContext) -> None:
        """Handle a deactivate message."""
        self._enabled = False
        self.logger.info(
            AgentEvent(
                f"{self.metadata['type']} (deactivated)",
                "",
            )
        )

    async def on_unhandled_message(self, message: Any, ctx: MessageContext) -> None:
        """Drop the message, with a log."""
        # self.logger.info(
        #     AgentEvent(
        #         f"{self.metadata['type']} (unhandled message)",
        #         f"Unhandled message type: {type(message)}",
        #     )
        # )
        pass
