from typing import Any, Dict, List, Mapping, Optional

from autogen_core.components.models import (
    AssistantMessage,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from pydantic import BaseModel, Field, field_validator

from ..messages import (
    AgentMessage,
    ChatMessage,
    HandoffMessage,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ToolCallMessage,
    ToolCallResultMessage,
)


class BaseState(BaseModel):
    """Base class for all saveable state"""

    type: str = Field(default="BaseState")
    version: str = Field(default="1.0.0")


class AssistantAgentState(BaseState):
    """State for an assistant agent."""

    model_context: List[LLMMessage] = Field(default_factory=list)
    type: str = Field(default="AssistantAgentState")

    @field_validator("model_context", mode="before")
    def validate_model_context(cls, value: List[LLMMessage] | List[Dict[str, Any]]) -> List[LLMMessage]:
        if not isinstance(value, list):
            raise ValueError("model_context must be a list")
        model_context: List[LLMMessage] = []
        for msg in value:
            if isinstance(msg, UserMessage | SystemMessage | AssistantMessage | FunctionExecutionResultMessage):
                if msg.type not in [
                    "UserMessage",
                    "AssistantMessage",
                    "SystemMessage",
                    "FunctionExecutionResultMessage",
                ]:
                    raise ValueError(f"Invalid message type field: {msg.type}")
                model_context.append(msg)
            elif isinstance(msg, dict):
                if msg.get("type") == "UserMessage":
                    model_context.append(UserMessage(**msg))
                elif msg.get("type") == "AssistantMessage":
                    model_context.append(AssistantMessage(**msg))
                elif msg.get("type") == "SystemMessage":
                    model_context.append(SystemMessage(**msg))
                elif msg.get("type") == "FunctionExecutionResultMessage":
                    model_context.append(FunctionExecutionResultMessage(**msg))
                else:
                    raise ValueError(f"Invalid item type: {msg.get('type')}")
        return model_context


class TeamState(BaseState):
    """State for a team of agents."""

    agent_states: Mapping[str, Any] = Field(default_factory=dict)
    team_id: str = Field(default="")
    type: str = Field(default="TeamState")


class BaseGroupChatManagerState(BaseState):
    """Base state for all group chat managers."""

    message_thread: List[AgentMessage] = Field(default_factory=list)
    current_turn: int = Field(default=0)
    type: str = Field(default="BaseGroupChatManagerState")

    @field_validator("message_thread", mode="before")
    def validate_message_thread(cls, value: List[AgentMessage] | List[Dict[str, Any]]) -> List[AgentMessage]:
        if not isinstance(value, list):
            raise ValueError("message_thread must be a list")
        message_thread: List[AgentMessage] = []
        for msg in value:
            if isinstance(msg, AgentMessage):
                if msg.type not in [
                    "TextMessage",
                    "MultiModalMessage",
                    "StopMessage",
                    "HandoffMessage",
                    "ToolCallMessage",
                    "ToolCallResultMessage",
                ]:
                    raise ValueError(f"Invalid message type field: {msg.type}")
                message_thread.append(msg)
            elif isinstance(msg, dict):
                if msg.get("type") == "TextMessage":
                    message_thread.append(TextMessage.model_validate(msg))
                elif msg.get("type") == "MultiModalMessage":
                    message_thread.append(MultiModalMessage.model_validate(msg))
                elif msg.get("type") == "StopMessage":
                    message_thread.append(StopMessage.model_validate(msg))
                elif msg.get("type") == "HandoffMessage":
                    message_thread.append(HandoffMessage.model_validate(msg))
                elif msg.get("type") == "ToolCallMessage":
                    message_thread.append(ToolCallMessage.model_validate(msg))
                elif msg.get("type") == "ToolCallResultMessage":
                    message_thread.append(ToolCallResultMessage.model_validate(msg))
                else:
                    raise ValueError(f"Invalid item type: {msg.get('type')}")
        return message_thread


class ChatAgentContainerState(BaseState):
    """State for a container of chat agents."""

    agent_state: Mapping[str, Any] = Field(default_factory=dict)
    message_buffer: List[ChatMessage] = Field(default_factory=list)
    type: str = Field(default="ChatAgentContainerState")

    @field_validator("message_buffer", mode="before")
    def validate_message_buffer(cls, value: List[ChatMessage] | List[Dict[str, Any]]) -> List[ChatMessage]:
        if not isinstance(value, list):
            raise ValueError("message_buffer must be a list")
        message_buffer: List[ChatMessage] = []
        for msg in value:
            if isinstance(msg, ChatMessage):
                if msg.type not in ["TextMessage", "MultiModalMessage", "StopMessage", "HandoffMessage"]:
                    raise ValueError(f"Invalid message type field: {msg.type}")
                message_buffer.append(msg)
            elif isinstance(msg, dict):
                if msg.get("type") == "TextMessage":
                    message_buffer.append(TextMessage.model_validate(msg))
                elif msg.get("type") == "MultiModalMessage":
                    message_buffer.append(MultiModalMessage.model_validate(msg))
                elif msg.get("type") == "StopMessage":
                    message_buffer.append(StopMessage.model_validate(msg))
                elif msg.get("type") == "HandoffMessage":
                    message_buffer.append(HandoffMessage.model_validate(msg))
                else:
                    raise ValueError(f"Invalid item type: {msg.get('type')}")
        return message_buffer


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
