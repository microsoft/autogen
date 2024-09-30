import logging
import time
from typing import List, Optional

from autogen_core.application.logging import EVENT_LOGGER_NAME
from autogen_core.base import AgentProxy, CancellationToken, MessageContext
from autogen_core.components.models import AssistantMessage, LLMMessage, UserMessage

from ..messages import BroadcastMessage, OrchestrationEvent, RequestReplyMessage, ResetMessage
from ..utils import message_content_to_str
from .base_agent import TeamOneBaseAgent


class BaseOrchestrator(TeamOneBaseAgent):
    def __init__(
        self,
        agents: List[AgentProxy],
        description: str = "Base orchestrator",
        max_rounds: int = 20,
        max_time: float = float("inf"),
        handle_messages_concurrently: bool = False,
    ) -> None:
        super().__init__(description, handle_messages_concurrently=handle_messages_concurrently)
        self._agents = agents
        self._max_rounds = max_rounds
        self._max_time = max_time
        self._num_rounds = 0
        self._start_time: float = -1.0
        self.logger = logging.getLogger(EVENT_LOGGER_NAME + f".{self.id.key}.orchestrator")

    async def _handle_broadcast(self, message: BroadcastMessage, ctx: MessageContext) -> None:
        """Handle an incoming message."""

        # First broadcast sets the timer
        if self._start_time < 0:
            self._start_time = time.time()

        source = "Unknown"
        if isinstance(message.content, UserMessage) or isinstance(message.content, AssistantMessage):
            source = message.content.source

        content = message_content_to_str(message.content.content)

        self.logger.info(OrchestrationEvent(source, content))

        # Termination conditions
        if self._num_rounds >= self._max_rounds:
            self.logger.info(
                OrchestrationEvent(
                    f"{self.metadata['type']} (termination condition)",
                    f"Max rounds ({self._max_rounds}) reached.",
                )
            )
            return

        if time.time() - self._start_time >= self._max_time:
            self.logger.info(
                OrchestrationEvent(
                    f"{self.metadata['type']} (termination condition)",
                    f"Max time ({self._max_time}s) reached.",
                )
            )
            return

        if message.request_halt:
            self.logger.info(
                OrchestrationEvent(
                    f"{self.metadata['type']} (termination condition)",
                    f"{source} requested halt.",
                )
            )
            return

        next_agent = await self._select_next_agent(message.content)
        if next_agent is None:
            self.logger.info(
                OrchestrationEvent(
                    f"{self.metadata['type']} (termination condition)",
                    "No agent selected.",
                )
            )
            return
        request_reply_message = RequestReplyMessage()
        # emit an event

        self.logger.info(
            OrchestrationEvent(
                source=f"{self.metadata['type']} (thought)",
                message=f"Next speaker {(await next_agent.metadata)['type']}" "",
            )
        )

        self._num_rounds += 1  # Call before sending the message
        await self.send_message(request_reply_message, next_agent.id, cancellation_token=ctx.cancellation_token)

    async def _select_next_agent(self, message: LLMMessage) -> Optional[AgentProxy]:
        raise NotImplementedError()

    def get_max_rounds(self) -> int:
        return self._max_rounds

    async def _handle_reset(self, message: ResetMessage, ctx: MessageContext) -> None:
        """Handle a reset message."""
        await self._reset(ctx.cancellation_token)

    async def _reset(self, cancellation_token: CancellationToken) -> None:
        pass
