import os
from typing import Any

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def get_chat_completion_client_from_envs(**kwargs: Any) -> ChatCompletionClient:
    # Check API type.
    api_type = os.getenv("OPENAI_API_TYPE", "openai")
    if api_type == "openai":
        # Check API key.
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError("OPENAI_API_KEY is not set")
        kwargs["api_key"] = api_key
        return OpenAIChatCompletionClient(**kwargs)
    elif api_type == "azure":
        # Check Azure API key.
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if azure_api_key is not None:
            kwargs["api_key"] = azure_api_key
        else:
            # Try to use token from Azure CLI.
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )
            kwargs["azure_ad_token_provider"] = token_provider
        # Check Azure API endpoint.
        azure_api_endpoint = os.getenv("AZURE_OPENAI_API_ENDPOINT")
        if azure_api_endpoint is None:
            raise ValueError("AZURE_OPENAI_API_ENDPOINT is not set")
        kwargs["azure_endpoint"] = azure_api_endpoint
        # Get Azure API version.
        kwargs["api_version"] = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
        # Set model capabilities.
        if "model_capabilities" not in kwargs or kwargs["model_capabilities"] is None:
            kwargs["model_capabilities"] = {
                "vision": True,
                "function_calling": True,
                "json_output": True,
            }
        return AzureOpenAIChatCompletionClient(**kwargs)  # type: ignore
    raise ValueError(f"Unknown API type: {api_type}")
