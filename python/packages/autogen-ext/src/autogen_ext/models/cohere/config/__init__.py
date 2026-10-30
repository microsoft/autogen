"""Configuration classes for Cohere chat completion client."""

from typing import Any, Dict, List, Literal, Optional, Union

from autogen_core.models import ModelCapabilities, ModelInfo  # type: ignore
from pydantic import BaseModel, SecretStr
from typing_extensions import Required, TypedDict


class ResponseFormat(TypedDict, total=False):
    """Response format configuration for Cohere."""

    type: Required[Literal["text", "json_object"]]
    json_schema: Optional[Dict[str, Any]]


class CreateArguments(TypedDict, total=False):
    """Arguments for creating a Cohere chat completion."""

    model: str
    max_tokens: Optional[int]
    temperature: Optional[float]
    p: Optional[float]
    k: Optional[int]
    seed: Optional[int]
    stop_sequences: Optional[List[str]]
    frequency_penalty: Optional[float]
    presence_penalty: Optional[float]
    response_format: Optional[ResponseFormat]
    tool_choice: Optional[Literal["REQUIRED", "NONE"]]
    logprobs: Optional[bool]
    safety_mode: Optional[Literal["CONTEXTUAL", "STRICT", "OFF"]]


class CohereClientConfiguration(CreateArguments, total=False):
    """Configuration for Cohere chat completion client."""

    api_key: str
    base_url: Optional[str]
    model_capabilities: ModelCapabilities  # type: ignore
    model_info: ModelInfo
    """What functionality the model supports, determined by default from model name but is overridden if value passed."""
    timeout: Optional[float]
    max_retries: Optional[int]
    client_name: Optional[str]


# Pydantic equivalents of the above TypedDicts
class CreateArgumentsConfigModel(BaseModel):
    """Pydantic model for create arguments."""

    model: str
    max_tokens: int | None = None
    temperature: float | None = 0.3
    p: float | None = None
    k: int | None = None
    seed: int | None = None
    stop_sequences: List[str] | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    response_format: ResponseFormat | None = None
    tool_choice: Literal["REQUIRED", "NONE"] | None = None
    logprobs: bool | None = None
    safety_mode: Literal["CONTEXTUAL", "STRICT", "OFF"] | None = None


class CohereClientConfigurationConfigModel(CreateArgumentsConfigModel):
    """Pydantic model for Cohere client configuration."""

    api_key: SecretStr | None = None
    base_url: str | None = None
    model_capabilities: ModelCapabilities | None = None  # type: ignore
    model_info: ModelInfo | None = None
    timeout: float | None = None
    max_retries: int | None = None
    client_name: str | None = None


__all__ = [
    "CreateArguments",
    "CreateArgumentsConfigModel",
    "CohereClientConfiguration",
    "CohereClientConfigurationConfigModel",
    "ResponseFormat",
]
