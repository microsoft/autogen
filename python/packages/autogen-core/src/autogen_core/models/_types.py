from dataclasses import dataclass
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from .. import FunctionCall, Image


class SystemMessage(BaseModel):
    """System message contains instructions for the model coming from the developer.

    .. note::

        Open AI is moving away from using 'system' role in favor of 'developer' role.
        See `Model Spec <https://cdn.openai.com/spec/model-spec-2024-05-08.html#definitions>`_ for more details.
        However, the 'system' role is still allowed in their API and will be automatically converted to 'developer' role
        on the server side.
        So, you can use `SystemMessage` for developer messages.

    """

    content: str
    """The content of the message."""

    type: Literal["SystemMessage"] = "SystemMessage"


class UserMessage(BaseModel):
    """User message contains input from end users, or a catch-all for data provided to the model."""

    content: Union[str, List[Union[str, Image]]]
    """The content of the message."""

    source: str
    """The name of the agent that sent this message."""

    type: Literal["UserMessage"] = "UserMessage"


class AssistantMessage(BaseModel):
    """Assistant message are sampled from the language model."""

    content: Union[str, List[FunctionCall]]
    """The content of the message."""

    thought: str | None = None
    """The reasoning text for the completion if available. Used for reasoning model and additional text content besides function calls."""

    source: str
    """The name of the agent that sent this message."""

    type: Literal["AssistantMessage"] = "AssistantMessage"


class FunctionExecutionResult(BaseModel):
    """Function execution result contains the output of a function call."""

    content: str
    """The output of the function call."""

    name: str
    """(New in v0.4.8) The name of the function that was called."""

    call_id: str
    """The ID of the function call. Note this ID may be empty for some models."""

    is_error: bool | None = None
    """Whether the function call resulted in an error."""


class FunctionExecutionResultMessage(BaseModel):
    """Function execution result message contains the output of multiple function calls."""

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
    """Create result contains the output of a model completion."""

    finish_reason: FinishReasons
    """The reason the model finished generating the completion."""

    content: Union[str, List[FunctionCall]]
    """The output of the model completion."""

    usage: RequestUsage
    """The usage of tokens in the prompt and completion."""

    cached: bool
    """Whether the completion was generated from a cached response."""

    logprobs: Optional[List[ChatCompletionTokenLogprob] | None] = None
    """The logprobs of the tokens in the completion."""

    thought: Optional[str] = None
    """The reasoning text for the completion if available. Used for reasoning models
    and additional text content besides function calls."""
