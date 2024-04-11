from typing import List, Optional

from autogen.experimental.agent import Agent
from autogen.experimental.termination import TerminationManager, TerminationReason, TerminationResult

from ..types import AssistantMessage, MessageAndSender, UserMessage


class DefaultTerminationManager(TerminationManager):
    def __init__(self, *, termination_message: str = "TERMINATE", max_turns: int = 10) -> None:
        self._termination_message = termination_message
        self._max_turns = max_turns
        self._turns = 0

    def record_turn_taken(self, agent: Agent) -> None:
        self._turns += 1

    async def check_termination(self, chat_history: List[MessageAndSender]) -> Optional[TerminationResult]:
        if self._turns >= self._max_turns:
            return TerminationResult(TerminationReason.MAX_TURNS_REACHED, "Max turns reached.")

        messages = [message.message for message in chat_history]
        # TODO handle tool message
        for message in messages:
            if isinstance(message, UserMessage):
                if message.is_termination:
                    return TerminationResult(TerminationReason.USER_REQUESTED, "User requested termination.")
                elif self._termination_message in message.content:
                    return TerminationResult(TerminationReason.TERMINATION_MESSAGE, "Termination message received.")
            if isinstance(message, AssistantMessage):
                if message.content is not None and self._termination_message in message.content:
                    return TerminationResult(TerminationReason.TERMINATION_MESSAGE, "Termination message received.")

        return None

    def reset(self) -> None:
        self._turns = 0
