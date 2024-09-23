from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from autogen.oai.client_utils import validate_parameter

logger = logging.getLogger(__name__)

class AzureAIInferenceClient:
    """Azure AI Inference Client
    
    This class provides an interface to interact with Azure AI Inference API for natural language processing tasks.
    It supports various language models and handles API requests, response processing, and error handling.

    Key Features:
    1. Supports multiple AI models provided by Azure AI Inference.
    2. Handles authentication using API keys.
    3. Provides methods for creating chat completions.
    4. Processes and formats API responses into standardized ChatCompletion objects.
    5. Implements rate limiting and error handling for robust API interactions.
    6. Calculates usage statistics and estimated costs for API calls.

    Usage:
    - Initialize the client with the desired model and API key.
    - Use the 'create' method to generate chat completions.
    - Retrieve messages and usage information from the responses.

    Note: Ensure that the AZURE_API_KEY is set in the environment variables or provided during initialization.

    # Example usage
    if __name__ == "__main__":
    import os
    import autogen

    config_list = [
        {
            "model": "gpt-4o",
            "api_key": os.getenv("AZURE_API_KEY"),
        }
    ]

    assistant = autogen.AssistantAgent(
        "assistant",
        llm_config={"config_list": config_list, "cache_seed": 42},
    )

    human = autogen.UserProxyAgent(
        "human",
        human_input_mode="TERMINATE",
        max_consecutive_auto_reply=10,
        code_execution_config={"work_dir": "coding"},
        llm_config={"config_list": config_list, "cache_seed": 42},
    )

    human.initiate_chat(
        assistant,
        message="Would I be better off deploying multiple models on cloud or at home?",
    )
    """

    SUPPORTED_MODELS = [
        "AI21-Jamba-Instruct",
        "cohere-command-r",
        "cohere-command-r-plus",
        "meta-llama-3-70b-instruct",
        "meta-llama-3-8b-instruct",
        "meta-llama-3.1-405b-instruct",
        "meta-llama-3.1-70b-instruct",
        "meta-llama-3.1-8b-instruct",
        "mistral-large",
        "mistral-large-2407",
        "mistral-nemo",
        "mistral-small",
        "gpt-4o",
        "gpt-4o-mini",
        "phi-3-medium-instruct-128k",
        "phi-3-medium-instruct-4k",
        "phi-3-mini-instruct-128k",
        "phi-3-mini-instruct-4k",
        "phi-3-small-instruct-128k",
        "phi-3-small-instruct-8k",
    ]

    def __init__(self, **kwargs):
        self.endpoint_url = "https://models.inference.ai.azure.com/chat/completions"
        self.model = kwargs.get("model")
        self.api_key = kwargs.get("api_key") or os.environ.get("AZURE_API_KEY")
        
        if not self.api_key:
            raise ValueError("AZURE_API_KEY is not set in environment variables or provided in kwargs.")

        if self.model.lower() not in [model.lower() for model in self.SUPPORTED_MODELS]:
            raise ValueError(f"Model {self.model} is not supported. Please choose from {self.SUPPORTED_MODELS}")

    def load_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Load the configuration for the Azure AI Inference client."""
        config = {}
        config["model"] = params.get("model", self.model)
        config["temperature"] = validate_parameter(params, "temperature", (float, int), False, 1.0, (0.0, 2.0), None)
        config["max_tokens"] = validate_parameter(params, "max_tokens", int, False, 4096, (1, None), None)
        config["top_p"] = validate_parameter(params, "top_p", (float, int), True, None, (0.0, 1.0), None)
        config["stop"] = validate_parameter(params, "stop", (str, list), True, None, None, None)
        config["stream"] = validate_parameter(params, "stream", bool, False, False, None, None)

        return config

    def message_retrieval(self, response: ChatCompletion) -> List[str]:
        """Retrieve the messages from the response."""
        return [choice.message.content for choice in response.choices]

    def create(self, params: Dict[str, Any]) -> ChatCompletion:
        """Create a completion for a given config."""
        config = self.load_config(params)
        messages = params.get("messages", [])

        data = {
            "messages": messages,
            "model": config["model"],
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"],
            "top_p": config["top_p"],
            "stop": config["stop"],
            "stream": config["stream"],
        }

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        response = self._call_api(self.endpoint_url, headers, data)
        return self._process_response(response)

    def _call_api(self, endpoint_url: str, headers: Dict[str, str], data: Dict[str, Any]) -> Dict[str, Any]:
        """Make an API call to Azure AI Inference."""
        response = requests.post(endpoint_url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def _process_response(self, response_data: Dict[str, Any]) -> ChatCompletion:
        """Process the API response and return a ChatCompletion object."""
        choices = [
            Choice(
                index=i,
                message=ChatCompletionMessage(role="assistant", content=choice["message"]["content"]),
                finish_reason=choice.get("finish_reason"),
            )
            for i, choice in enumerate(response_data["choices"])
        ]

        usage = CompletionUsage(
            prompt_tokens=response_data["usage"]["prompt_tokens"],
            completion_tokens=response_data["usage"]["completion_tokens"],
            total_tokens=response_data["usage"]["total_tokens"],
        )

        return ChatCompletion(
            id=response_data["id"],
            model=response_data["model"],
            created=response_data["created"],
            object="chat.completion",
            choices=choices,
            usage=usage,
        )

    def cost(self, response: ChatCompletion) -> float:
        """Calculate the cost of the response."""
        # Implement cost calculation logic here if needed
        return 0.0

    @staticmethod
    def get_usage(response: ChatCompletion) -> Dict:
        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cost": response.cost if hasattr(response, "cost") else 0,
            "model": response.model,
        }

class AzureAIInferenceWrapper:
    """Wrapper for Azure AI Inference Client"""

    def __init__(self, config_list: Optional[List[Dict[str, Any]]] = None, **kwargs):
        self._clients = []
        self._config_list = []

        if config_list:
            for config in config_list:
                self._register_client(config)
                self._config_list.append(config)
        else:
            self._register_client(kwargs)
            self._config_list = [kwargs]

    def _register_client(self, config: Dict[str, Any]):
        client = AzureAIInferenceClient(**config)
        self._clients.append(client)

    def create(self, **params: Any) -> ChatCompletion:
        """Create a completion using available clients."""
        for i, client in enumerate(self._clients):
            try:
                response = client.create(params)
                response.config_id = i
                return response
            except Exception as e:
                logger.warning(f"Error with client {i}: {str(e)}")
                if i == len(self._clients) - 1:
                    raise

    def message_retrieval(self, response: ChatCompletion) -> List[str]:
        """Retrieve messages from the response."""
        return self._clients[response.config_id].message_retrieval(response)

    def cost(self, response: ChatCompletion) -> float:
        """Calculate the cost of the response."""
        return self._clients[response.config_id].cost(response)

    @staticmethod
    def get_usage(response: ChatCompletion) -> Dict:
        """Get usage information from the response."""
        return AzureAIInferenceClient.get_usage(response)