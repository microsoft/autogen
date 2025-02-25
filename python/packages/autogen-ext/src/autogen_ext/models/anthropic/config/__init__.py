from typing import Any, Dict, List, Literal, Optional, Union

from autogen_core.models import ModelCapabilities, ModelInfo  # type: ignore
from pydantic import BaseModel
from typing_extensions import TypedDict


class ResponseFormat(TypedDict):
    type: Literal["text", "json_object"]


class CreateArguments(TypedDict, total=False):
    model: str
    max_tokens: Optional[int]
    temperature: Optional[float]
    top_p: Optional[float]
    top_k: Optional[int]
    stop_sequences: Optional[List[str]]
    response_format: Optional[ResponseFormat]
    metadata: Optional[Dict[str, str]]


class BaseAnthropicClientConfiguration(CreateArguments, total=False):
    api_key: str
    base_url: Optional[str]
    model_capabilities: ModelCapabilities  # type: ignore
    model_info: ModelInfo
    """What functionality the model supports, determined by default from model name but is overridden if value passed."""
    timeout: Optional[float]
    max_retries: Optional[int]
    default_headers: Optional[Dict[str, str]]


class AnthropicClientConfiguration(BaseAnthropicClientConfiguration, total=False):
    tools: Optional[List[Dict[str, Any]]]
    tool_choice: Optional[Union[Literal["auto", "any", "none"], Dict[str, Any]]]


# Pydantic equivalents of the above TypedDicts
class CreateArgumentsConfigModel(BaseModel):
    model: str
    max_tokens: int | None = 4096
    temperature: float | None = 1.0
    top_p: float | None = None
    top_k: int | None = None
    stop_sequences: List[str] | None = None
    response_format: ResponseFormat | None = None
    metadata: Dict[str, str] | None = None


class BaseAnthropicClientConfigurationConfigModel(CreateArgumentsConfigModel):
    api_key: str | None = None
    base_url: str | None = None
    model_capabilities: ModelCapabilities | None = None  # type: ignore
    model_info: ModelInfo | None = None
    timeout: float | None = None
    max_retries: int | None = None
    default_headers: Dict[str, str] | None = None


class AnthropicClientConfigurationConfigModel(BaseAnthropicClientConfigurationConfigModel):
    tools: List[Dict[str, Any]] | None = None
    tool_choice: Union[Literal["auto", "any", "none"], Dict[str, Any]] | None = None
