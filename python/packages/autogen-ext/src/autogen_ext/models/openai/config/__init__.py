from typing import Awaitable, Callable, Dict, List, Literal, Optional, Union

from autogen_core import ComponentModel
from autogen_core.models import ModelCapabilities, ModelInfo  # type: ignore
from pydantic import BaseModel
from typing_extensions import Required, TypedDict


class ResponseFormat(TypedDict):
    type: Literal["text", "json_object"]


class CreateArguments(TypedDict, total=False):
    frequency_penalty: Optional[float]
    logit_bias: Optional[Dict[str, int]]
    max_tokens: Optional[int]
    n: Optional[int]
    presence_penalty: Optional[float]
    response_format: ResponseFormat
    seed: Optional[int]
    stop: Union[Optional[str], List[str]]
    temperature: Optional[float]
    top_p: Optional[float]
    user: str


AsyncAzureADTokenProvider = Callable[[], Union[str, Awaitable[str]]]


class BaseOpenAIClientConfiguration(CreateArguments, total=False):
    model: str
    api_key: str
    timeout: Union[float, None]
    max_retries: int
    model_capabilities: ModelCapabilities  # type: ignore
    model_info: ModelInfo
    """What functionality the model supports, determined by default from model name but is overriden if value passed."""


# See OpenAI docs for explanation of these parameters
class OpenAIClientConfiguration(BaseOpenAIClientConfiguration, total=False):
    organization: str
    base_url: str


class AzureOpenAIClientConfiguration(BaseOpenAIClientConfiguration, total=False):
    # Azure specific
    azure_endpoint: Required[str]
    azure_deployment: str
    api_version: Required[str]
    azure_ad_token: str
    azure_ad_token_provider: AsyncAzureADTokenProvider  # Or AzureTokenProvider


__all__ = [
    "AzureOpenAIClientConfiguration",
    "OpenAIClientConfiguration",
    "AzureOpenAIClientConfigurationConfigModel",
    "OpenAIClientConfigurationConfigModel",
]


# Pydantic equivalents of the above TypedDicts


class CreateArgumentsConfigModel(BaseModel):
    frequency_penalty: float | None = None
    logit_bias: Dict[str, int] | None = None
    max_tokens: int | None = None
    n: int | None = None
    presence_penalty: float | None = None
    response_format: ResponseFormat | None = None
    seed: int | None = None
    stop: str | List[str] | None = None
    temperature: float | None = None
    top_p: float | None = None
    user: str | None = None


class BaseOpenAIClientConfigurationConfigModel(CreateArgumentsConfigModel):
    model: str
    api_key: str | None = None
    timeout: float | None = None
    max_retries: int | None = None
    model_capabilities: ModelCapabilities | None = None  # type: ignore
    model_info: ModelInfo | None = None


# See OpenAI docs for explanation of these parameters
class OpenAIClientConfigurationConfigModel(BaseOpenAIClientConfigurationConfigModel):
    organization: str | None = None
    base_url: str | None = None


class AzureOpenAIClientConfigurationConfigModel(BaseOpenAIClientConfigurationConfigModel):
    # Azure specific
    azure_endpoint: str
    azure_deployment: str | None = None
    api_version: str
    azure_ad_token: str | None = None
    azure_ad_token_provider: ComponentModel | None = None
