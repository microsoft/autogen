from dataclasses import dataclass
from typing import List, Literal, Optional, Union, Any  # Added Any

from pydantic import BaseModel, Field, field_validator  # Added field_validator
from typing_extensions import Annotated

from .. import FunctionCall, Image, File, Media
# Need to import base64 for the validator
import base64


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

    content: Union[str, List[Union[str, Media]]]
    """The content of the message."""

    source: str
    """The name of the agent that sent this message."""

    type: Literal["UserMessage"] = "UserMessage"

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: Any) -> Union[str, List[Union[str, Media]]]:
        if isinstance(value, str):
            return value
        elif isinstance(value, list):
            validated_list = []
            for item in value:
                if isinstance(item, (str, Media)):
                    # Media is the base class for Image and File, so this will accept both
                    validated_list.append(item)
                elif isinstance(item, dict):
                    # Attempt to validate dicts as Media subclasses by trying instantiation
                    validated = False
                    
                    # Try Image first (expects 'data' key with base64)
                    if 'data' in item and len(item) == 1:  # Simple check for Image dict format
                        try:
                            validated_list.append(Image.from_base64(item['data']))
                            validated = True
                        except (ValueError, TypeError, KeyError, base64.binascii.Error):
                            pass  # Not a valid Image dict

                    # Try File if Image failed (expects 'filename', 'data', optional 'mime_type')
                    if not validated and 'filename' in item and 'data' in item:
                        try:
                            mime_type = item.get('mime_type')
                            validated_list.append(File.from_base64(item['data'], item['filename'], mime_type))
                            validated = True
                        except (ValueError, TypeError, KeyError, base64.binascii.Error):
                            pass  # Not a valid File dict

                    if not validated:
                        raise TypeError(f"Invalid dictionary format in content list: {item}. Expected dict representing a Media subclass.")
                else:
                    raise TypeError(f"Invalid type in content list: {type(item)}. Expected str, Media subclass, or dict.")
            return validated_list
        else:
            raise TypeError(f"Invalid type for content: {type(value)}. Expected str or list.")


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
