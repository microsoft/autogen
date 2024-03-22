
from typing import List, Optional, Union
from typing_extensions import Literal, Required, TypedDict


class Function(TypedDict, total=False):
    # JSON
    arguments: Required[str]
    name: Required[str]

class ToolCall(TypedDict, total=False):
    id: Required[str]
    function: Required[Function]
    type: Required[Literal["function"]]

class RequestUsage(TypedDict, total=False):
    prompt_tokens: Required[int]
    completion_tokens: Required[int]
    total_tokens: Required[int]
    cost: float
    model: Required[str]

class UserMessageContentPartText(TypedDict, total=False):
    text: Required[str]
    type: Required[Literal["text"]]

class ImageURL(TypedDict, total=False):
    url: Required[str]
    detail: Literal["auto", "low", "high"]

class UserMessageContentPartImage(TypedDict, total=False):
    image_url: Required[ImageURL]
    type: Required[Literal["image_url"]]

UserMessageContentPart = Union[UserMessageContentPartText, UserMessageContentPartImage]

class SystemMessage(TypedDict, total=False):
    content: Required[Optional[str]]
    role: Required[Literal["system"]]

class UserMessage(TypedDict, total=False):
    content: Required[Union[str, List[UserMessageContentPart]]]
    role: Required[Literal["user"]]

class AssistantMessage(TypedDict, total=False):
    content: Required[Optional[str]]
    role: Required[Literal["assistant"]]
    tool_calls: List[ToolCall]

class ToolMessage(TypedDict, total=False):
    content: Required[Optional[str]]
    role: Required[Literal["tool"]]
    tool_call_id: Required[str]

ChatMessage = Union[SystemMessage, UserMessage, AssistantMessage, ToolMessage]

class CreateResponse(TypedDict, total=False):
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter"]
    content: Required[Union[str, List[ToolCall]]]
    usage: Optional[RequestUsage]