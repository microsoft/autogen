from autogen_core.base import AgentId
from pydantic import BaseModel, ConfigDict

from ..agents import MultiModalMessage, StopMessage, TextMessage, ToolCallMessage, ToolCallResultMessage


class ContentPublishEvent(BaseModel):
    """An event for sharing some data. Agents receive this event should
    update their internal state (e.g., append to message history) with the
    content of the event.
    """

    agent_message: TextMessage | MultiModalMessage | StopMessage
    """The message published by the agent."""

    source: AgentId | None = None
    """The agent ID that published the message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ContentRequestEvent(BaseModel):
    """An event for requesting to publish a content event.
    Upon receiving this event, the agent should publish a ContentPublishEvent.
    """

    ...


class ToolCallEvent(BaseModel):
    """An event produced when requesting a tool call."""

    agent_message: ToolCallMessage
    """The tool call message."""

    source: AgentId
    """The sender of the tool call message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ToolCallResultEvent(BaseModel):
    """An event produced when a tool call is completed."""

    agent_message: ToolCallResultMessage
    """The tool call result message."""

    source: AgentId
    """The sender of the tool call result message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SelectSpeakerEvent(BaseModel):
    """An event for selecting the next speaker in a group chat."""

    selected_speaker: str
    """The name of the selected speaker."""

    source: AgentId
    """The agent ID that selected the speaker."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TerminationEvent(BaseModel):
    """An event for terminating a conversation."""

    agent_message: StopMessage
    """The stop message that terminates the conversation."""

    source: AgentId
    """The agent ID that triggered the termination."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
