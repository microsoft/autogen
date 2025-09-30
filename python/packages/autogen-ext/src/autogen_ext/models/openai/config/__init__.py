from typing import Awaitable, Callable, Dict, List, Literal, Optional, Union

from autogen_core import ComponentModel
from autogen_core.models import ModelCapabilities, ModelInfo  # type: ignore
from pydantic import BaseModel, SecretStr
from typing_extensions import Required, TypedDict


class JSONSchema(TypedDict, total=False):
    name: Required[str]
    """The name of the response format. Must be a-z, A-Z, 0-9, or contain underscores and
    dashes, with a maximum length of 64."""
    description: str
    """A description of what the response format is for, used by the model to determine
    how to respond in the format."""
    schema: Dict[str, object]
    """The schema for the response format, described as a JSON Schema object."""
    strict: Optional[bool]
    """Whether to enable strict schema adherence when generating the output.
    If set to true, the model will always follow the exact schema defined in the
    `schema` field. Only a subset of JSON Schema is supported when `strict` is
    `true`. To learn more, read the
    [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).
    """


class ResponseFormat(TypedDict):
    type: Literal["text", "json_object", "json_schema"]
    """The type of response format being defined: `text`, `json_object`, or `json_schema`"""

    json_schema: Optional[JSONSchema]
    """The type of response format being defined: `json_schema`"""


class StreamOptions(TypedDict):
    include_usage: bool


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
    stream_options: Optional[StreamOptions]
    parallel_tool_calls: Optional[bool]
    reasoning_effort: Optional[Literal["minimal", "low", "medium", "high"]]
    """Controls the amount of effort the model uses for reasoning.
    Only applicable to reasoning models like o1 and o3-mini.
    - 'low': Faster responses with less reasoning
    - 'medium': Balanced reasoning and speed
    - 'high': More thorough reasoning, may take longer"""


AsyncAzureADTokenProvider = Callable[[], Union[str, Awaitable[str]]]


class BaseOpenAIClientConfiguration(CreateArguments, total=False):
    model: str
    api_key: str
    timeout: Union[float, None]
    max_retries: int
    model_capabilities: ModelCapabilities  # type: ignore
    model_info: ModelInfo
    add_name_prefixes: bool
    """What functionality the model supports, determined by default from model name but is overriden if value passed."""
    include_name_in_message: bool
    """Whether to include the 'name' field in user message parameters. Defaults to True. Set to False for providers that don't support the 'name' field."""
    default_headers: Dict[str, str] | None


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
    stream_options: StreamOptions | None = None
    parallel_tool_calls: bool | None = None
    # Controls the amount of effort the model uses for reasoning (reasoning models only)
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None


class BaseOpenAIClientConfigurationConfigModel(CreateArgumentsConfigModel):
    model: str
    api_key: SecretStr | None = None
    timeout: float | None = None
    max_retries: int | None = None
    model_capabilities: ModelCapabilities | None = None  # type: ignore
    model_info: ModelInfo | None = None
    add_name_prefixes: bool | None = None
    include_name_in_message: bool | None = None
    default_headers: Dict[str, str] | None = None


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
