from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from typing_extensions import Literal, NotRequired, Required, TypedDict


@dataclass
class FunctionCall:
    id: str
    # JSON args
    arguments: str
    # Function to call
    name: str


@dataclass
class FunctionDefinition:
    name: str
    parameters: Dict[str, Any]
    description: str


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
    function_calls: Optional[List[FunctionCall]] = None


@dataclass
class FunctionCallResult:
    content: str
    tool_call_id: str


@dataclass
class FunctionCallMessage:
    call_results: List[FunctionCallResult]


ChatMessage = Union[SystemMessage, UserMessage, AssistantMessage, FunctionCallMessage]


@dataclass
class PartialContent:
    content: str


@dataclass
class StatusUpdate:
    content: str


# Must end with ChatMessage
StreamResponse = Union[PartialContent, StatusUpdate, ChatMessage]
FinishReasons = Literal["stop", "length", "function_calls", "content_filter"]


@dataclass
class CreateResponse:
    finish_reason: FinishReasons
    content: Union[str, List[FunctionCall]]
    usage: RequestUsage
    cached: bool


@dataclass
class ToolDefinition:
    name: str
    parameters: Dict[str, Any]
    description: str = ""
