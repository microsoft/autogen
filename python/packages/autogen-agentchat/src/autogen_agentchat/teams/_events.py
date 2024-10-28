from autogen_core.base import AgentId
from pydantic import BaseModel, ConfigDict

from ..messages import ChatMessage, StopMessage


class GroupChatPublishEvent(BaseModel):
    """An group chat event for sharing some data. Agents receive this event should
    update their internal state (e.g., append to message history) with the
    content of the event.
    """

    agent_message: ChatMessage
    """The message published by the agent."""

    source: AgentId | None = None
    """The agent ID that published the message."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class GroupChatRequestPublishEvent(BaseModel):
    """An event for requesting to publish a group chat publish event.
    Upon receiving this event, the agent should publish a group chat publish event.
    """

    ...


class GroupChatSelectSpeakerEvent(BaseModel):
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
