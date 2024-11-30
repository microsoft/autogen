from dataclasses import dataclass, field
from typing import List, Optional

from ._base import BaseState


@dataclass(kw_only=True)
class BaseTerminationState(BaseState):
    """Base class for all termination condition states"""

    terminated: bool = False
    state_type: str = field(default="BaseTerminationState")
    version: str = field(default="1.0.0")

    def __post_init__(self) -> None:
        super().__post_init__()


@dataclass(kw_only=True)
class StopMessageTerminationState(BaseTerminationState):
    """State for conditions that terminate based on a stop message"""

    state_type: str = field(default="StopMessageTerminationState")


@dataclass(kw_only=True)
class MaxMessageTerminationState(BaseTerminationState):
    """State for conditions that terminate after a maximum number of messages"""

    message_count: int = 0
    max_messages: int = 0
    state_type: str = field(default="MaxMessageTerminationState")


@dataclass(kw_only=True)
class TextMentionTerminationState(BaseTerminationState):
    """State for conditions that terminate when specific text is mentioned"""

    text: str = ""
    state_type: str = field(default="TextMentionTerminationState")


@dataclass(kw_only=True)
class TokenUsageTerminationState(BaseTerminationState):
    """State for conditions that terminate based on token usage"""

    total_token_count: int = 0
    prompt_token_count: int = 0
    completion_token_count: int = 0
    max_total_token: Optional[int] = None
    max_prompt_token: Optional[int] = None
    max_completion_token: Optional[int] = None
    state_type: str = field(default="TokenUsageTerminationState")


@dataclass(kw_only=True)
class HandoffTerminationState(BaseTerminationState):
    """State for conditions that terminate with a handoff to another target"""

    target: str = ""
    state_type: str = field(default="HandoffTerminationState")


@dataclass(kw_only=True)
class TimeoutTerminationState(BaseTerminationState):
    """State for conditions that terminate after a timeout period"""

    start_time: float = 0.0
    timeout_seconds: float = 0.0
    state_type: str = field(default="TimeoutTerminationState")


@dataclass(kw_only=True)
class ExternalTerminationState(BaseTerminationState):
    """State for conditions that terminate based on external signals"""

    setted: bool = False  # Indicates if external termination has been set
    state_type: str = field(default="ExternalTerminationState")


@dataclass(kw_only=True)
class SourceMatchTerminationState(BaseTerminationState):
    """State for conditions that terminate based on matching sources"""

    sources: List[str] = field(default_factory=list)
    state_type: str = field(default="SourceMatchTerminationState")


@dataclass(kw_only=True)
class AndTerminationState(BaseTerminationState):
    """State for AND combinations of termination conditions"""

    condition_states: List[BaseTerminationState] = field(default_factory=list)
    stop_messages: List[str] = field(
        default_factory=list)  # Serialized stop messages
    state_type: str = field(default="AndTerminationState")


@dataclass(kw_only=True)
class OrTerminationState(BaseTerminationState):
    """State for OR combinations of termination conditions"""

    condition_states: List[BaseTerminationState] = field(default_factory=list)
    state_type: str = field(default="OrTerminationState")
