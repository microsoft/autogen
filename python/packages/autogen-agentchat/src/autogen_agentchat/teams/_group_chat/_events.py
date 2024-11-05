from pydantic import BaseModel

from ...base import Response
from ...messages import AgentMessage, ChatMessage, StopMessage


class GroupChatStart(BaseModel):
    """A request to start a group chat."""

    message: ChatMessage
    """The user message that started the group chat."""


class GroupChatAgentResponse(BaseModel):
    """A response published to a group chat."""

    agent_response: Response
    """The response from an agent."""


class GroupChatRequestPublish(BaseModel):
    """A request to publish a message to a group chat."""

    ...


class GroupChatMessage(BaseModel):
    """A message from a group chat."""

    message: AgentMessage
    """The message that was published."""


class GroupChatTermination(BaseModel):
    """A message indicating that a group chat has terminated."""

    message: StopMessage
    """The stop message that indicates the reason of termination."""
