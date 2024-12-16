from typing import TypedDict, Union, Optional, List, Dict, Any
from azure.ai.inference.models import (
    ChatCompletionsResponseFormat,
    ChatCompletionsToolDefinition,
    ChatCompletionsToolChoicePreset,
    ChatCompletionsNamedToolChoice,
)

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from autogen_core.models import ModelCapabilities

GITHUB_MODELS_ENDPOINT = "https://models.inference.ai.azure.com"


class AzureAIClientArguments(TypedDict, total=False):
    endpoint: str
    credential: Union[AzureKeyCredential, AsyncTokenCredential]
    model_capabilities: ModelCapabilities


class AzureAICreateArguments(TypedDict, total=False):
    frequency_penalty: Optional[float]
    presence_penalty: Optional[float]
    temperature: Optional[float]
    top_p: Optional[float]
    max_tokens: Optional[int]
    response_format: Optional[ChatCompletionsResponseFormat]
    stop: Optional[List[str]]
    tools: Optional[List[ChatCompletionsToolDefinition]]
    tool_choice: Optional[Union[str, ChatCompletionsToolChoicePreset, ChatCompletionsNamedToolChoice]]
    seed: Optional[int]
    model: Optional[str]
    model_extras: Optional[Dict[str, Any]]


class AzureAIChatCompletionClientConfig(AzureAIClientArguments, AzureAICreateArguments):
    pass
