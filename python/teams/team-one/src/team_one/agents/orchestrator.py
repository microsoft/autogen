import logging
from typing import List

from agnext.application.logging import EVENT_LOGGER_NAME
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import AssistantMessage, UserMessage
from agnext.core import AgentProxy, CancellationToken

from ..messages import BroadcastMessage, OrchestrationEvent, RequestReplyMessage

logger = logging.getLogger(EVENT_LOGGER_NAME + ".orchestrator")


class RoundRobinOrchestrator(TypeRoutedAgent):
    def __init__(
        self,
        agents: List[AgentProxy],
        description: str = "Round robin orchestrator",
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

        content = str(message.content.content)

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

        next_agent = self._select_next_agent()
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

    def _select_next_agent(self) -> AgentProxy:
        self._current_index = (self._num_rounds) % len(self._agents)
        return self._agents[self._current_index]
