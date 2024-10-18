from typing import List, Tuple

from autogen_core.base import CancellationToken, MessageContext, TopicId
from autogen_core.components.models import (
    AssistantMessage,
    LLMMessage,
    UserMessage,
)

from autogen_magentic_one.messages import (
    BroadcastMessage,
    RequestReplyMessage,
    ResetMessage,
    UserContent,
)

from ..utils import message_content_to_str
from .base_agent import MagenticOneBaseAgent


class BaseWorker(MagenticOneBaseAgent):
    """Base agent that handles the MagenticOne worker behavior protocol."""

    def __init__(
        self,
        description: str,
        handle_messages_concurrently: bool = False,
    ) -> None:
        super().__init__(description, handle_messages_concurrently=handle_messages_concurrently)
        self._chat_history: List[LLMMessage] = []

    async def _handle_broadcast(self, message: BroadcastMessage, ctx: MessageContext) -> None:
        assert isinstance(message.content, UserMessage)
        self._chat_history.append(message.content)

    async def _handle_reset(self, message: ResetMessage, ctx: MessageContext) -> None:
        """Handle a reset message."""
        await self._reset(ctx.cancellation_token)

    async def _handle_request_reply(self, message: RequestReplyMessage, ctx: MessageContext) -> None:
        """Respond to a reply request."""
        request_halt, response = await self._generate_reply(ctx.cancellation_token)

        assistant_message = AssistantMessage(content=message_content_to_str(response), source=self.metadata["type"])
        self._chat_history.append(assistant_message)

        user_message = UserMessage(content=response, source=self.metadata["type"])
        topic_id = TopicId("default", self.id.key)
        await self.publish_message(
            BroadcastMessage(content=user_message, request_halt=request_halt),
            topic_id=topic_id,
            cancellation_token=ctx.cancellation_token,
        )

    async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, UserContent]:
        """Returns (request_halt, response_message)"""
        raise NotImplementedError()

    async def _reset(self, cancellation_token: CancellationToken) -> None:
        self._chat_history = []
