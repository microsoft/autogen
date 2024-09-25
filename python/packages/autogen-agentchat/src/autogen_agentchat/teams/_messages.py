from autogen_core.components.models import AssistantMessage, UserMessage
from pydantic import BaseModel


class ContentPublishEvent(BaseModel):
    """An event message for sharing some data. Agents receive this message should
    update their internal state (e.g., append to message history) with the
    content of the message.
    """

    content: UserMessage | AssistantMessage
    """The content of the message."""

    request_pause: bool
    """A flag indicating whether the current conversation session should be
    paused after processing this message."""


class ContentRequestEvent(BaseModel):
    """An event message for requesting to publish a content message.
    Upon receiving this message, the agent should publish a ContentPublishEvent
    message.
    """

    ...
