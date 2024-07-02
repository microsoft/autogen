import logging
from datetime import datetime
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
    ) -> None:
        super().__init__(description)
        self._agents = agents
        self._num_rounds = 0

    @message_handler
    async def handle_incoming_message(self, message: BroadcastMessage, cancellation_token: CancellationToken) -> None:
        """Handle an incoming message."""
        source = "Unknown"
        if isinstance(message.content, UserMessage) or isinstance(message.content, AssistantMessage):
            source = message.content.source

        assert isinstance(source, str)

        current_timestamp = datetime.now().isoformat()
        logger.info(
            OrchestrationEvent(
                current_timestamp,
                f"""
-------------------------------------
{source}: {message.content.content}
-------------------------------------
""",
            )
        )

        if self._num_rounds > 20:
            return

        next_agent = self._select_next_agent()
        request_reply_message = RequestReplyMessage()
        # emit an event

        current_timestamp = datetime.now().isoformat()
        logger.info(
            OrchestrationEvent(
                current_timestamp,
                f"Orchestrator (thought): Next speaker {next_agent.metadata['name']}",
            )
        )

        await self.send_message(request_reply_message, next_agent.id)

        self._num_rounds += 1

    def _select_next_agent(self) -> AgentProxy:
        self._current_index = (self._num_rounds) % len(self._agents)
        return self._agents[self._current_index]
