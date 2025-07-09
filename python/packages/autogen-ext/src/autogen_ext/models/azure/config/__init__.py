from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from autogen_core.models import ModelInfo
from azure.ai.inference.models import (
    ChatCompletionsNamedToolChoice,
    ChatCompletionsToolChoicePreset,
    ChatCompletionsToolDefinition,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential

GITHUB_MODELS_ENDPOINT = "https://models.github.ai/inference"


class JsonSchemaFormat(TypedDict, total=False):
    """Represents the same fields as azure.ai.inference.models.JsonSchemaFormat."""

    name: str
    schema: Dict[str, Any]
    description: Optional[str]
    strict: Optional[bool]


class AzureAIClientArguments(TypedDict, total=False):
    """Arguments for AzureAI clients.

    Required fields:
    - endpoint (str): The endpoint to use.
    - credential (Union[AzureKeyCredential, AsyncTokenCredential]): The credentials to use.
    - model_info (ModelInfo): The model family and capabilities of the model.

    Optional fields:
    - api_version (str): API version to use when calling Azure AI Service.
    """

    endpoint: str
    credential: Union[AzureKeyCredential, AsyncTokenCredential]
    model_info: ModelInfo
    api_version: Optional[str]


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
