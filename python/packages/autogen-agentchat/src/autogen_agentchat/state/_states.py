from typing import Annotated, Any, Dict, List, Mapping, Optional, Self

from pydantic import BaseModel, Field

from ..messages import (
    AgentEvent,
    ChatMessage,
    StructuredMessage,
)

# Ensures pydantic can distinguish between types of events & messages.
_AgentMessage = Annotated[AgentEvent | ChatMessage, Field(discriminator="type")]


class BaseState(BaseModel):
    """Base class for all saveable state"""

    type: str = Field(default="BaseState")
    version: str = Field(default="1.0.0")


class AssistantAgentState(BaseState):
    """State for an assistant agent."""

    llm_context: Mapping[str, Any] = Field(default_factory=lambda: dict([("messages", [])]))
    type: str = Field(default="AssistantAgentState")


class TeamState(BaseState):
    """State for a team of agents."""

    agent_states: Mapping[str, Any] = Field(default_factory=dict)
    type: str = Field(default="TeamState")


class BaseGroupChatManagerState(BaseState):
    """Base state for all group chat managers."""

    message_thread: List[_AgentMessage] = Field(default_factory=list)
    current_turn: int = Field(default=0)
    type: str = Field(default="BaseGroupChatManagerState")

    def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Override model_dump to ensure StructuredMessage is handled properly."""
        state = super().model_dump(*args, **kwargs)
        for i, message in enumerate(self.message_thread):
            if isinstance(message, StructuredMessage):
                state["message_thread"][i] = message.dump()
        return state

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> Self:
        """Override model_validate to ensure message_thread is handled properly for StructuredMessage."""
        messages = obj["message_thread"]
        instance = super().model_validate(obj, **kwargs)
        for i, message in enumerate(messages):
            # For each message, check if it's a structured message and validate it
            # If it is, replace it with the validated instance
            # Otherwise, leave it as is.
            if message["type"] == "StructuredMessage":
                structured_message = StructuredMessage[BaseModel].load(message)
                instance.message_thread[i] = structured_message
        return instance


class ChatAgentContainerState(BaseState):
    """State for a container of chat agents."""

    agent_state: Mapping[str, Any] = Field(default_factory=dict)
    message_buffer: List[ChatMessage] = Field(default_factory=list)
    type: str = Field(default="ChatAgentContainerState")

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Override model_dump to ensure StructuredMessage is handled properly."""
        state = super().model_dump(*args, **kwargs)
        for i, message in enumerate(self.message_buffer):
            if isinstance(message, StructuredMessage):
                state["message_buffer"][i] = message.dump()
        return state

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> Self:
        """Override model_validate to ensure message_buffer is handled properly for StructuredMessage."""
        messages = obj["message_buffer"]
        instance = super().model_validate(obj, **kwargs)
        for i, message in enumerate(messages):
            # For each message, check if it's a structured message and validate it
            # If it is, replace it with the validated instance
            # Otherwise, leave it as is.
            if message["type"] == "StructuredMessage":
                structured_message = StructuredMessage[BaseModel].load(message)
                instance.message_buffer[i] = structured_message
        return instance


class RoundRobinManagerState(BaseGroupChatManagerState):
    """State for :class:`~autogen_agentchat.teams.RoundRobinGroupChat` manager."""

    next_speaker_index: int = Field(default=0)
    type: str = Field(default="RoundRobinManagerState")


class SelectorManagerState(BaseGroupChatManagerState):
    """State for :class:`~autogen_agentchat.teams.SelectorGroupChat` manager."""

    previous_speaker: Optional[str] = Field(default=None)
    type: str = Field(default="SelectorManagerState")


class SwarmManagerState(BaseGroupChatManagerState):
    """State for :class:`~autogen_agentchat.teams.Swarm` manager."""

    current_speaker: str = Field(default="")
    type: str = Field(default="SwarmManagerState")


class MagenticOneOrchestratorState(BaseGroupChatManagerState):
    """State for :class:`~autogen_agentchat.teams.MagneticOneGroupChat` orchestrator."""

    task: str = Field(default="")
    facts: str = Field(default="")
    plan: str = Field(default="")
    n_rounds: int = Field(default=0)
    n_stalls: int = Field(default=0)
    type: str = Field(default="MagenticOneOrchestratorState")


class SocietyOfMindAgentState(BaseState):
    """State for a Society of Mind agent."""

    inner_team_state: Mapping[str, Any] = Field(default_factory=dict)
    type: str = Field(default="SocietyOfMindAgentState")
