from dataclasses import dataclass
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from .. import FunctionCall, Image


class SystemMessage(BaseModel):
    content: str
    type: Literal["SystemMessage"] = "SystemMessage"


class UserMessage(BaseModel):
    content: Union[str, List[Union[str, Image]]]

    # Name of the agent that sent this message
    source: str

    type: Literal["UserMessage"] = "UserMessage"


class AssistantMessage(BaseModel):
    content: Union[str, List[FunctionCall]]

    # Name of the agent that sent this message
    source: str

    type: Literal["AssistantMessage"] = "AssistantMessage"


class FunctionExecutionResult(BaseModel):
    content: str
    call_id: str


class FunctionExecutionResultMessage(BaseModel):
    content: List[FunctionExecutionResult]

    type: Literal["FunctionExecutionResultMessage"] = "FunctionExecutionResultMessage"


LLMMessage = Annotated[
    Union[SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage], Field(discriminator="type")
]


@dataclass
class RequestUsage:
    prompt_tokens: int
    completion_tokens: int


FinishReasons = Literal["stop", "length", "function_calls", "content_filter", "unknown"]


@dataclass
class TopLogprob:
    logprob: float
    bytes: Optional[List[int]] = None


class ChatCompletionTokenLogprob(BaseModel):
    token: str
    logprob: float
    top_logprobs: Optional[List[TopLogprob] | None] = None
    bytes: Optional[List[int]] = None


class CreateResult(BaseModel):
    finish_reason: FinishReasons
    content: Union[str, List[FunctionCall]]
    usage: RequestUsage
    cached: bool
    logprobs: Optional[List[ChatCompletionTokenLogprob] | None] = None
