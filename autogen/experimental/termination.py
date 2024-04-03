from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Protocol

from autogen.experimental.agent import Agent

from .types import ChatMessage


class TerminationReason(Enum):
    MAX_TURNS_REACHED = "max_turns_reached"
    TERMINATION_MESSAGE = "termination_message"
    GOAL_REACHED = "goal_reached"
    INSUFFICIENT_PROGRESS = "insufficient_progress"
    USER_REQUESTED = "user_requested"


@dataclass
class TerminationResult:
    reason: TerminationReason
    explanation: Optional[str]


class TerminationManager(Protocol):
    def record_turn_taken(self, agent: Agent) -> None: ...

    async def check_termination(self, chat_history: List[ChatMessage]) -> Optional[TerminationResult]: ...

    def reset(self) -> None: ...
