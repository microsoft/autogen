from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..messages import AgentMessage
from ._base import BaseState
from ._termination_states import BaseTerminationState


@dataclass(kw_only=True)
class BaseGroupChatManagerState(BaseState):
    """Base state for all group chat managers."""

    message_thread: List[AgentMessage] = field(default_factory=list)
    current_turn: int = field(default=0)
    state_type: str = field(default="BaseGroupChatManagerState")


@dataclass(kw_only=True)
class BaseTeamState(BaseState):
    """Base state for all team types."""

    agent_names: List[str] = field(default_factory=list)
    termination_state: Optional[BaseTerminationState] = field(default=None)
    agent_states: Dict[str, BaseState] = field(default_factory=dict)
    manager_state: BaseGroupChatManagerState = field(default_factory=BaseGroupChatManagerState)
    state_type: str = field(default="BaseTeamState")


@dataclass(kw_only=True)
class RoundRobinManagerState(BaseGroupChatManagerState):
    """State for round robin group chat manager."""

    next_speaker_index: int = field(default=0)
    state_type: str = field(default="RoundRobinManagerState")


@dataclass(kw_only=True)
class SelectorManagerState(BaseGroupChatManagerState):
    """State for selector group chat manager."""

    previous_speaker: Optional[str] = field(default=None)
    state_type: str = field(default="SelectorManagerState")


@dataclass(kw_only=True)
class SwarmManagerState(BaseGroupChatManagerState):
    """State for swarm group chat manager."""

    current_speaker: str = field(default="")
    state_type: str = field(default="SwarmManagerState")
