from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Union

from typing_extensions import Literal

from .image import Image


@dataclass
class FunctionCall:
    id: str
    # JSON args
    arguments: str
    # Function to call
    name: str


@dataclass
class FunctionSignature:
    name: str
    parameters: Dict[str, Any]
    description: str


@dataclass
class RequestUsage:
    prompt_tokens: int
    completion_tokens: int


@dataclass
class SystemMessage:
    content: str


@dataclass
class UserMessage:
    content: Union[str, List[Union[str, Image]]]

    # Name of the agent that sent this message
    source: str


@dataclass
class AssistantMessage:
    content: Union[str, List[FunctionCall]]

    # Name of the agent that sent this message
    source: str


@dataclass
class FunctionExecutionResult:
    content: str
    call_id: str


@dataclass
class FunctionExecutionResultMessage:
    content: List[FunctionExecutionResult]


LLMMessage = Union[SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage]


FinishReasons = Literal["stop", "length", "function_calls", "content_filter"]


@dataclass
class CreateResult:
    finish_reason: FinishReasons
    content: Union[str, List[FunctionCall]]
    usage: RequestUsage
    cached: bool
