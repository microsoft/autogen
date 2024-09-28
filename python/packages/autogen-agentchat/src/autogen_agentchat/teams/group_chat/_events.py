from pydantic import BaseModel

from ...agents import MultiModalMessage, StopMessage, TextMessage


class ContentPublishEvent(BaseModel):
    """An event for sharing some data. Agents receive this event should
    update their internal state (e.g., append to message history) with the
    content of the event.
    """

    agent_message: TextMessage | MultiModalMessage | StopMessage
    """The message published by the agent."""


class ContentRequestEvent(BaseModel):
    """An event for requesting to publish a content event.
    Upon receiving this event, the agent should publish a ContentPublishEvent.
    """

    ...
