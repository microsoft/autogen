from dataclasses import dataclass, field
from typing import List, Optional

from ._base import BaseState


@dataclass
class StopMessageTerminationState(BaseState):
    terminated: bool  # Required state
    state_type: str = field(default="StopMessageTerminationState")
    version: str = field(default="1.0.0")


@dataclass
class MaxMessageTerminationState(BaseState):
    max_messages: int  # Required state
    message_count: int  # Required state
    state_type: str = field(default="MaxMessageTerminationState")
    version: str = field(default="1.0.0")


@dataclass
class TextMentionTerminationState(BaseState):
    text: str  # Required state
    terminated: bool  # Required state
    state_type: str = field(default="TextMentionTerminationState")
    version: str = field(default="1.0.0")


@dataclass
class TokenUsageTerminationState(BaseState):
    total_token_count: int  # Required state
    prompt_token_count: int  # Required state
    completion_token_count: int  # Required state
    max_total_token: Optional[int]  # Required state (can be None)
    max_prompt_token: Optional[int]  # Required state (can be None)
    max_completion_token: Optional[int]  # Required state (can be None)
    state_type: str = field(default="TokenUsageTerminationState")
    version: str = field(default="1.0.0")


@dataclass
class HandoffTerminationState(BaseState):
    target: str  # Required state
    terminated: bool  # Required state
    state_type: str = field(default="HandoffTerminationState")
    version: str = field(default="1.0.0")


@dataclass
class TimeoutTerminationState(BaseState):
    timeout_seconds: float  # Required state
    start_time: float  # Required state
    terminated: bool  # Required state
    state_type: str = field(default="TimeoutTerminationState")
    version: str = field(default="1.0.0")


@dataclass
class ExternalTerminationState(BaseState):
    terminated: bool  # Required state
    setted: bool  # Required state
    state_type: str = field(default="ExternalTerminationState")
    version: str = field(default="1.0.0")


@dataclass
class SourceMatchTerminationState(BaseState):
    sources: List[str]  # Required state
    terminated: bool  # Required state
    state_type: str = field(default="SourceMatchTerminationState")
    version: str = field(default="1.0.0")

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.sources, list):
            raise ValueError("sources must be a list")
