import traceback
from typing import List

from pydantic import BaseModel

from ...base import Response
from ...messages import BaseAgentEvent, BaseChatMessage, StopMessage


class SerializableException(BaseModel):
    """A serializable exception."""

    error_type: str
    """The type of error that occurred."""

    error_message: str
    """The error message that describes the error."""

    traceback: str | None = None
    """The traceback of the error, if available."""

    @classmethod
    def from_exception(cls, exc: Exception) -> "SerializableException":
        """Create a GroupChatError from an exception."""
        return cls(
            error_type=type(exc).__name__,
            error_message=str(exc),
            traceback="\n".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        )

    def __str__(self) -> str:
        """Return a string representation of the error, including the traceback if available."""
        if self.traceback:
            return f"{self.error_type}: {self.error_message}\nTraceback:\n{self.traceback}"
        return f"{self.error_type}: {self.error_message}"


class GroupChatStart(BaseModel):
    """A request to start a group chat."""

    messages: List[BaseChatMessage] | None = None
    """An optional list of messages to start the group chat."""

    output_task_messages: bool = True
    """Whether to include task messages in the output. Defaults to True for backward compatibility."""


class GroupChatAgentResponse(BaseModel):
    """A response published to a group chat."""

    agent_response: Response
    """The response from an agent."""

    agent_name: str
    """The name of the agent that produced the response."""


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

    error: SerializableException | None = None
    """The error that occurred, if any."""


class GroupChatReset(BaseModel):
    """A request to reset the agents in the group chat."""

    ...


class GroupChatPause(BaseModel):
    """A request to pause the group chat."""

    ...


class GroupChatResume(BaseModel):
    """A request to resume the group chat."""

    ...


class GroupChatError(BaseModel):
    """A message indicating that an error occurred in the group chat."""

    error: SerializableException
    """The error that occurred."""
