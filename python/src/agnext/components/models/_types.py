from dataclasses import dataclass
from typing import List, Literal, Optional, Union

from .. import FunctionCall, Image


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


@dataclass
class RequestUsage:
    prompt_tokens: int
    completion_tokens: int


FinishReasons = Literal["stop", "length", "function_calls", "content_filter"]


@dataclass
class TopLogprob:
    logprob: float
    bytes: Optional[List[int]] = None


@dataclass
class ChatCompletionTokenLogprob:
    token: str
    logprob: float
    top_logprobs: Optional[List[TopLogprob] | None] = None
    bytes: Optional[List[int]] = None


@dataclass
class CreateResult:
    finish_reason: FinishReasons
    content: Union[str, List[FunctionCall]]
    usage: RequestUsage
    cached: bool
    logprobs: Optional[List[ChatCompletionTokenLogprob] | None] = None
