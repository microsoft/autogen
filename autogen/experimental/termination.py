from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol, Union

from .agent import Agent
from .chat_history import ChatHistoryReadOnly


class TerminationReason(Enum):
    MAX_TURNS_REACHED = "max_turns_reached"
    TERMINATION_MESSAGE = "termination_message"
    GOAL_REACHED = "goal_reached"
    INSUFFICIENT_PROGRESS = "insufficient_progress"
    USER_REQUESTED = "user_requested"


@dataclass
class Terminated:
    reason: TerminationReason
    explanation: Optional[str]


@dataclass
class NotTerminated:
    explanation: Optional[str] = None


TerminationResult = Union[Terminated, NotTerminated]


# TODO allow termination to have an understanding of cost
class Termination(Protocol):
    def record_turn_taken(self, agent: Agent) -> None: ...

    async def check_termination(self, chat_history: ChatHistoryReadOnly) -> TerminationResult: ...

    def reset(self) -> None: ...
