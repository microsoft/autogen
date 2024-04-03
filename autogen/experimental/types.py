from typing import Any, Dict, List, Optional, Union
from typing_extensions import Literal, Required, TypedDict, NotRequired
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    # JSON args
    arguments: str
    # Function to call
    name: str


@dataclass
class RequestUsage:
    prompt_tokens: int
    completion_tokens: int
    cost: Optional[float]


@dataclass
class UserMessageContentPartText:
    text: str


@dataclass
class ImageURL:
    url: str
    detail: Literal["auto", "low", "high"] = "auto"


@dataclass
class UserMessageContentPartImage:
    image_url: ImageURL
    type: Literal["image_url"]


UserMessageContentPart = Union[UserMessageContentPartText, UserMessageContentPartImage]


@dataclass
class SystemMessage:
    content: str


@dataclass
class UserMessage:
    content: Union[str, List[UserMessageContentPart]]
    is_termination: bool = False


@dataclass
class AssistantMessage:
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


@dataclass
class ToolResponse:
    content: str
    tool_call_id: str


@dataclass
class ToolMessage:
    responses: List[ToolResponse]


ChatMessage = Union[SystemMessage, UserMessage, AssistantMessage, ToolMessage]


@dataclass
class CreateResponse:
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter"]
    content: Union[str, List[ToolCall]]
    usage: RequestUsage
    cached: bool


@dataclass
class ToolDefinition:
    name: str
    parameters: Dict[str, Any]
    description: str = ""
