from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..messages import AgentMessage
from ._base import BaseState
from ._termination_states import BaseTerminationState


@dataclass(kw_only=True)
class BaseGroupChatManagerState(BaseState):
    """Base state for all group chat managers.

    Attributes:
        message_thread: List of messages in the conversation
        current_turn: Current turn number in the conversation
        state_type: Type identifier for this state class
    """

    message_thread: List[AgentMessage] = field(default_factory=list)
    current_turn: int = field(default=0)
    state_type: str = field(default="BaseGroupChatManagerState")


@dataclass(kw_only=True)
class RoundRobinManagerState(BaseGroupChatManagerState):
    """State for round robin group chat manager.

    Attributes:
        next_speaker_index: Index of the next speaker in rotation
        state_type: Type identifier for this state class
    """

    next_speaker_index: int = field(default=0)
    state_type: str = field(default="RoundRobinManagerState")


@dataclass(kw_only=True)
class SelectorManagerState(BaseGroupChatManagerState):
    """State for selector group chat manager.

    Attributes:
        previous_speaker: Name of the previous speaker
        state_type: Type identifier for this state class
    """

    previous_speaker: Optional[str] = field(default=None)
    state_type: str = field(default="SelectorManagerState")


@dataclass(kw_only=True)
class SwarmManagerState(BaseGroupChatManagerState):
    """State for swarm group chat manager.

    Attributes:
        current_speaker: Name of the current speaker
        state_type: Type identifier for this state class
    """

    current_speaker: str = field(default="")
    state_type: str = field(default="SwarmManagerState")


@dataclass(kw_only=True)
class BaseTeamState(BaseState):
    """Base state for all team types.

    Attributes:
        agent_names: List of agent names in the team
        termination_state: State of the termination condition
        agent_states: Dictionary mapping agent names to their states
        manager_state: State of the group chat manager
        state_type: Type identifier for this state class
    """

    agent_names: List[str] = field(default_factory=list)
    termination_state: Optional[BaseTerminationState] = field(default=None)
    agent_states: Dict[str, BaseState] = field(default_factory=dict)
    manager_state: BaseGroupChatManagerState = field(default_factory=BaseGroupChatManagerState)
    state_type: str = field(default="BaseTeamState")
