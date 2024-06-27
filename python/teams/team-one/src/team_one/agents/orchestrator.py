from typing import List

from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import CancellationToken, AgentProxy

from ..messages import BroadcastMessage, RequestReplyMessage


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

        if self._num_rounds > 3:
            return

        next_agent = self._select_next_agent()
        request_reply_message = RequestReplyMessage()
        await self.send_message(request_reply_message, next_agent.id)

        self._num_rounds += 1

    def _select_next_agent(self) -> AgentProxy:
        self._current_index = (self._num_rounds) % len(self._agents)
        return self._agents[self._current_index]
