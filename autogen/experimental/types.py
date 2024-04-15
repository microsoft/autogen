from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from typing_extensions import Literal

from .agent import Agent
from .image import Image
from .termination import TerminationResult


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
class SystemMessage:
    content: str


@dataclass
class UserMessage:
    content: Union[str, List[Union[str, Image]]]
    is_termination: bool = False


@dataclass
class AssistantMessage:
    content: Optional[str] = None
    function_calls: Optional[List[FunctionCall]] = None


@dataclass
class FunctionCallResult:
    content: str
    call_id: str


@dataclass
class FunctionCallMessage:
    call_results: List[FunctionCallResult]


Message = Union[SystemMessage, UserMessage, AssistantMessage, FunctionCallMessage]


@dataclass
class ChatResult:
    chat_history: List[MessageAndSender]
    message_contexts: List[Optional[MessageContext]]
    summary: str
    termination_result: TerminationResult


@dataclass
class MessageAndSender:
    message: Message
    sender: Optional[Agent] = None


@dataclass
class MessageContext:
    # If this agent modified the input, this should be set
    input: Optional[List[Message]] = None

    # If this agent initiated a nested conversation, this should be set
    nested_chat_result: Optional[ChatResult] = None


FinishReasons = Literal["stop", "length", "function_calls", "content_filter"]


@dataclass
class CreateResult:
    finish_reason: FinishReasons
    content: Union[str, List[FunctionCall]]
    usage: RequestUsage
    cached: bool


@dataclass
class PartialContent:
    content: str


@dataclass
class StatusUpdate:
    content: str


@dataclass
class IntermediateResponse:
    item: Union[PartialContent, StatusUpdate]


GenerateReplyResult = Union[Message, Tuple[Message, MessageContext]]
