import logging
from typing import List, Optional

from agnext.application.logging import EVENT_LOGGER_NAME
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import AssistantMessage, LLMMessage, UserMessage
from agnext.core import AgentProxy, CancellationToken

from ..messages import BroadcastMessage, OrchestrationEvent, RequestReplyMessage
from ..utils import message_content_to_str

logger = logging.getLogger(EVENT_LOGGER_NAME + ".orchestrator")


class BaseOrchestrator(TypeRoutedAgent):
    def __init__(
        self,
        agents: List[AgentProxy],
        description: str = "Base orchestrator",
        max_rounds: int = 20,
    ) -> None:
        super().__init__(description)
        self._agents = agents
        self._max_rounds = max_rounds
        self._num_rounds = 0

    @message_handler
    async def handle_incoming_message(self, message: BroadcastMessage, cancellation_token: CancellationToken) -> None:
        """Handle an incoming message."""
        source = "Unknown"
        if isinstance(message.content, UserMessage) or isinstance(message.content, AssistantMessage):
            source = message.content.source

        content = message_content_to_str(message.content.content)

        logger.info(OrchestrationEvent(source, content))

        # Termination conditions
        if self._num_rounds >= self._max_rounds:
            logger.info(
                OrchestrationEvent(
                    f"{self.metadata['name']} (termination condition)",
                    f"Max rounds ({self._max_rounds}) reached.",
                )
            )
            return

        if message.request_halt:
            logger.info(
                OrchestrationEvent(
                    f"{self.metadata['name']} (termination condition)",
                    f"{source} requested halt.",
                )
            )
            return

        next_agent = await self._select_next_agent(message.content)
        if next_agent is None:
            logger.info(
                OrchestrationEvent(
                    f"{self.metadata['name']} (termination condition)",
                    "No agent selected.",
                )
            )
            return
        request_reply_message = RequestReplyMessage()
        # emit an event

        logger.info(
            OrchestrationEvent(
                source=f"{self.metadata['name']} (thought)",
                message=f"Next speaker {next_agent.metadata['name']}" "",
            )
        )

        self._num_rounds += 1  # Call before sending the message
        await self.send_message(request_reply_message, next_agent.id)

    async def _select_next_agent(self, message: LLMMessage) -> Optional[AgentProxy]:
        raise NotImplementedError()

    def get_max_rounds(self) -> int:
        return self._max_rounds
