from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Union

from autogen_core import FunctionCall, Image
from autogen_core.components.models import FunctionExecutionResultMessage


@dataclass(kw_only=True)
class BaseMessage:
    # Name of the agent that sent this message
    source: str


@dataclass
class TextMessage(BaseMessage):
    content: str


@dataclass
class MultiModalMessage(BaseMessage):
    content: List[Union[str, Image]]


@dataclass
class FunctionCallMessage(BaseMessage):
    content: List[FunctionCall]


Message = Union[TextMessage, MultiModalMessage, FunctionCallMessage, FunctionExecutionResultMessage]


class ResponseFormat(Enum):
    text = "text"
    json_object = "json_object"


@dataclass
class RespondNow:
    """A message to request a response from the addressed agent. The sender
    expects a response upon sening and waits for it synchronously."""

    response_format: ResponseFormat = field(default=ResponseFormat.text)


@dataclass
class PublishNow:
    """A message to request an event to be published to the addressed agent.
    Unlike RespondNow, the sender does not expect a response upon sending."""

    response_format: ResponseFormat = field(default=ResponseFormat.text)


@dataclass
class Reset: ...


@dataclass
class ToolApprovalRequest:
    """A message to request approval for a tool call. The sender expects a
    response upon sending and waits for it synchronously."""

    tool_call: FunctionCall


@dataclass
class ToolApprovalResponse:
    """A message to respond to a tool approval request. The response is sent
    synchronously."""

    tool_call_id: str
    approved: bool
    reason: str
