"""Create a Github LLM Client with Azure Fallback.

# Usage example:
if __name__ == "__main__":
    config = {
        "model": "gpt-4o",
        "system_prompt": "You are a knowledgeable history teacher.",
        "use_azure_fallback": True
    }

    wrapper = GithubWrapper(config_list=[config])

    response = wrapper.create(messages=[{"role": "user", "content": "What is the capital of France?"}])
    print(wrapper.message_retrieval(response)[0])

    conversation = [
        {"role": "user", "content": "Tell me about the French Revolution."},
        {"role": "assistant", "content": "The French Revolution was a period of major social and political upheaval in France that began in 1789 with the Storming of the Bastille and ended in the late 1790s with the ascent of Napoleon Bonaparte."},
        {"role": "user", "content": "What were the main causes?"}
    ]

    response = wrapper.create(messages=conversation)
    print(wrapper.message_retrieval(response)[0])
"""

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

from autogen.cache import Cache
from autogen.oai.client_utils import should_hide_tools, validate_parameter

logger = logging.getLogger(__name__)


class GithubClient:
    """GitHub LLM Client with Azure Fallback"""

    SUPPORTED_MODELS = [
        "AI21-Jamba-Instruct",
        "cohere-command-r",
        "cohere-command-r-plus",
        "cohere-embed-v3-english",
        "cohere-embed-v3-multilingual",
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
        self.github_endpoint_url = "https://models.inference.ai.azure.com/chat/completions"
        self.model = kwargs.get("model")
        self.system_prompt = kwargs.get("system_prompt", "You are a helpful assistant.")
        self.use_azure_fallback = kwargs.get("use_azure_fallback", True)
        self.rate_limit_reset_time = 0
        self.request_count = 0
        self.max_requests_per_minute = 15
        self.max_requests_per_day = 150

        self.github_token = os.environ.get("GITHUB_TOKEN")
        self.azure_api_key = os.environ.get("AZURE_API_KEY")

        if not self.github_token:
            raise ValueError("GITHUB_TOKEN environment variable is not set.")
        if self.use_azure_fallback and not self.azure_api_key:
            raise ValueError("AZURE_API_KEY environment variable is not set.")

        if self.model.lower() not in [model.lower() for model in self.SUPPORTED_MODELS]:
            raise ValueError(f"Model {self.model} is not supported. Please choose from {self.SUPPORTED_MODELS}")

    def message_retrieval(self, response: ChatCompletion) -> List[str]:
        """Retrieve the messages from the response."""
        return [choice.message.content for choice in response.choices]

    def create(self, params: Dict[str, Any]) -> ChatCompletion:
        """Create a completion for a given config."""
        messages = params.get("messages", [])

        if "system" not in [m["role"] for m in messages]:
            messages.insert(0, {"role": "system", "content": self.system_prompt})

        data = {"messages": messages, "model": self.model, **params}

        if self._check_rate_limit():
            try:
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.github_token}"}

                response = self._call_api(self.github_endpoint_url, headers, data)
                self._increment_request_count()
                return self._process_response(response)
            except (requests.exceptions.RequestException, ValueError) as e:
                logger.warning(f"GitHub API call failed: {str(e)}. Falling back to Azure.")

        if self.use_azure_fallback:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.azure_api_key}"}

            response = self._call_api(self.github_endpoint_url, headers, data)
            return self._process_response(response)
        else:
            raise ValueError("Rate limit reached and Azure fallback is disabled.")

    def _check_rate_limit(self) -> bool:
        """Check if the rate limit has been reached."""
        current_time = time.time()
        if current_time < self.rate_limit_reset_time:
            return False
        if self.request_count >= self.max_requests_per_minute:
            self.rate_limit_reset_time = current_time + 60
            self.request_count = 0
            return False
        return True

    def _increment_request_count(self):
        """Increment the request count."""
        self.request_count += 1

    def _call_api(self, endpoint_url: str, headers: Dict[str, str], data: Dict[str, Any]) -> Dict[str, Any]:
        """Make an API call to either GitHub or Azure."""
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
        # Pass
        return 0.0  # Placeholder

    @staticmethod
    def get_usage(response: ChatCompletion) -> Dict:
        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cost": response.cost if hasattr(response, "cost") else 0,
            "model": response.model,
        }


class GithubWrapper:
    """Wrapper for GitHub LLM Client"""

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
        client = GithubClient(**config)
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
        return GithubClient.get_usage(response)
