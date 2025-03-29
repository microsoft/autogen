from typing import List

from pydantic import BaseModel

from ...base import Response
from ...messages import BaseAgentEvent, BaseChatMessage, StopMessage


class GroupChatStart(BaseModel):
    """A request to start a group chat."""

    messages: List[BaseChatMessage] | None = None
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

    message: BaseAgentEvent | BaseChatMessage
    """The message that was published."""


class GroupChatTermination(BaseModel):
    """A message indicating that a group chat has terminated."""

    message: StopMessage
    """The stop message that indicates the reason of termination."""


class GroupChatReset(BaseModel):
    """A request to reset the agents in the group chat."""

    ...


class GroupChatPause(BaseModel):
    """A request to pause the group chat."""

    ...


class GroupChatResume(BaseModel):
    """A request to resume the group chat."""

    ...
