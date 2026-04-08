from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from autogen_core.models import ModelInfo
from azure.ai.inference.models import (
    ChatCompletionsNamedToolChoice,
    ChatCompletionsToolChoicePreset,
    ChatCompletionsToolDefinition,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from pydantic import BaseModel, SecretStr

GITHUB_MODELS_ENDPOINT = "https://models.github.ai/inference"


class JsonSchemaFormat(TypedDict, total=False):
    """Represents the same fields as azure.ai.inference.models.JsonSchemaFormat."""

    name: str
    schema: Dict[str, Any]
    description: Optional[str]
    strict: Optional[bool]


class AzureAIClientArguments(TypedDict, total=False):
    endpoint: str
    credential: Union[AzureKeyCredential, AsyncTokenCredential]
    model_info: ModelInfo


class AzureAICreateArguments(TypedDict, total=False):
    frequency_penalty: Optional[float]
    presence_penalty: Optional[float]
    temperature: Optional[float]
    top_p: Optional[float]
    max_tokens: Optional[int]
    response_format: Optional[Literal["text", "json_object"]]
    stop: Optional[List[str]]
    tools: Optional[List[ChatCompletionsToolDefinition]]
    tool_choice: Optional[Union[str, ChatCompletionsToolChoicePreset, ChatCompletionsNamedToolChoice]]
    seed: Optional[int]
    model: Optional[str]
    model_extras: Optional[Dict[str, Any]]


class AzureAIChatCompletionClientConfig(AzureAIClientArguments, AzureAICreateArguments):
    pass


class AzureAIChatCompletionClientConfigModel(BaseModel):
    """Pydantic config model for AzureAIChatCompletionClient serialization."""

    endpoint: str
    api_key: SecretStr | None = None
    model_info: ModelInfo
    model: str | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    response_format: Literal["text", "json_object"] | None = None
    stop: List[str] | None = None
    seed: int | None = None
    model_extras: Dict[str, Any] | None = None
