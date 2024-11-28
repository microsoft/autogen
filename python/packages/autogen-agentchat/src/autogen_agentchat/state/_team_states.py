from dataclasses import dataclass, field
from typing import Dict, List, Optional
from ..messages import AgentMessage
from ._base import BaseState


@dataclass
class BaseTeamState(BaseState):
    """Base state for all teams"""
    state_type: str = "BaseTeamState"
    agent_names: List[str] = field(default_factory=list)
    termination_state: Optional[BaseState] = field(default=None)
    agent_states: Dict[str, BaseState] = field(default_factory=dict)


@dataclass
class RoundRobinGroupChatState(BaseTeamState):
    state_type: str = "RoundRobinGroupChatState"
    next_speaker_index: int = 0
    message_thread: List[AgentMessage] = field(default_factory=list)


@dataclass
class SelectorGroupChatState(BaseTeamState):
    state_type: str = "SelectorGroupChatState"
    previous_speaker: Optional[str] = field(default=None)
    message_thread: List[AgentMessage] = field(default_factory=list)


@dataclass
class SwarmGroupChatState(BaseTeamState):
    state_type: str = "SwarmGroupChatState"
    current_speaker: str = field(default="")
    message_thread: List[AgentMessage] = field(default_factory=list)
