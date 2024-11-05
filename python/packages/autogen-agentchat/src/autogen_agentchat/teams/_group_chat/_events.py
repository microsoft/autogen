from pydantic import BaseModel

from ...base import Response
from ...messages import ChatMessage


class GroupChatStart(BaseModel):
    """A request to start a group chat."""

    user_message: ChatMessage
    """The user message that started the group chat."""


class GroupChatAgentResponse(BaseModel):
    """A response published to a group chat."""

    agent_response: Response


class GroupChatRequestPublish(BaseModel):
    """A request to publish a message to a group chat."""

    ...
