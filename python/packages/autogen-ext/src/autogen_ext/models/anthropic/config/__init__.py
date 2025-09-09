from typing import Any, Dict, List, Literal, Optional, Union

from autogen_core.models import ModelCapabilities, ModelInfo  # type: ignore
from pydantic import BaseModel, SecretStr
from typing_extensions import Required, TypedDict


class ResponseFormat(TypedDict):
    type: Literal["text", "json_object"]


class ThinkingConfig(TypedDict, total=False):
    """Configuration for thinking mode."""

    type: Required[Literal["enabled", "disabled"]]
    budget_tokens: Optional[int]  # Required if type is "enabled"


class CreateArguments(TypedDict, total=False):
    model: str
    max_tokens: Optional[int]
    temperature: Optional[float]
    top_p: Optional[float]
    top_k: Optional[int]
    stop_sequences: Optional[List[str]]
    response_format: Optional[ResponseFormat]
    metadata: Optional[Dict[str, str]]
    thinking: Optional[ThinkingConfig]


class BedrockInfo(TypedDict):
    """BedrockInfo is a dictionary that contains information about a bedrock's properties.
    It is expected to be used in the bedrock_info property of a model client.

    """

    aws_access_key: Required[str]
    """Access key for the aws account to gain bedrock model access"""
    aws_secret_key: Required[str]
    """Access secret key for the aws account to gain bedrock model access"""
    aws_session_token: Required[str]
    """aws session token for the aws account to gain bedrock model access"""
    aws_region: Required[str]
    """aws region for the aws account to gain bedrock model access"""


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


class AnthropicBedrockClientConfiguration(AnthropicClientConfiguration, total=False):
    bedrock_info: BedrockInfo


# Pydantic equivalents of the above TypedDicts
class ThinkingConfigModel(BaseModel):
    """Configuration for thinking mode."""

    type: Literal["enabled", "disabled"]
    budget_tokens: int | None = None  # Required if type is "enabled"


class CreateArgumentsConfigModel(BaseModel):
    model: str
    max_tokens: int | None = 4096
    temperature: float | None = 1.0
    top_p: float | None = None
    top_k: int | None = None
    stop_sequences: List[str] | None = None
    response_format: ResponseFormat | None = None
    metadata: Dict[str, str] | None = None
    thinking: ThinkingConfigModel | None = None


class BaseAnthropicClientConfigurationConfigModel(CreateArgumentsConfigModel):
    api_key: SecretStr | None = None
    base_url: str | None = None
    model_capabilities: ModelCapabilities | None = None  # type: ignore
    model_info: ModelInfo | None = None
    timeout: float | None = None
    max_retries: int | None = None
    default_headers: Dict[str, str] | None = None


class AnthropicClientConfigurationConfigModel(BaseAnthropicClientConfigurationConfigModel):
    tools: List[Dict[str, Any]] | None = None
    tool_choice: Union[Literal["auto", "any", "none"], Dict[str, Any]] | None = None


class BedrockInfoConfigModel(TypedDict):
    aws_access_key: Required[SecretStr]
    """Access key for the aws account to gain bedrock model access"""
    aws_session_token: Required[SecretStr]
    """aws session token for the aws account to gain bedrock model access"""
    aws_region: Required[str]
    """aws region for the aws account to gain bedrock model access"""
    aws_secret_key: Required[SecretStr]


class AnthropicBedrockClientConfigurationConfigModel(AnthropicClientConfigurationConfigModel):
    bedrock_info: BedrockInfoConfigModel | None = None
