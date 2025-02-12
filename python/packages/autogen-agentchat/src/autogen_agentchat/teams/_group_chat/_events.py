from typing import List

from pydantic import BaseModel

from ...base import Response
from ...messages import AgentEvent, ChatMessage, StopMessage


class GroupChatStart(BaseModel):
    """A request to start a group chat."""

    messages: List[ChatMessage] | None = None
    """An optional list of messages to start the group chat."""


class GroupChatAgentResponse(BaseModel):
    """A response published to a group chat."""

    agent_response: Response
    """The response from an agent."""


class GroupChatRequestPublish(BaseModel):
    """A request to publish a message to a group chat."""

    ...


class GroupChatMessage(BaseModel):
    """A message from a group chat."""

    message: AgentEvent | ChatMessage
    """The message that was published."""


class GroupChatTermination(BaseModel):
    """A message indicating that a group chat has terminated."""

    message: StopMessage
    """The stop message that indicates the reason of termination."""


class GroupChatReset(BaseModel):
    """A request to reset the agents in the group chat."""

    ...
