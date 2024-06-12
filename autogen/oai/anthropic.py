"""
Create an OpenAI API client for the Anthropic API.

Example usage:
Install the `anthropic` package by running `pip install --upgrade anthropic`.
- https://docs.anthropic.com/en/docs/quickstart-guide

import autogen

config_list = [
    {
        "model": "claude-3-sonnet-20240229",
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "api_type": "anthropic",
    }
]

assistant = autogen.AssistantAgent("assitant", llm_config={"config_list": config_list})
"""

import inspect
import json
import os
import warnings
from typing import Any, Dict, List, Union

from anthropic import Anthropic
from anthropic import __version__ as anthropic_version
from anthropic.types import Completion, Message
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from typing_extensions import Annotated

TOOL_ENABLED = anthropic_version >= "0.23.1"
if TOOL_ENABLED:
    from anthropic.types.beta.tools import ToolsBetaMessage
else:
    ToolsBetaMessage = objectcm

ANTHROPIC_PRICING_1k = {
    "claude-3-sonnet-20240229": (0.003, 0.015),
    "claude-2.0": (0.008, 0.024),
    "claude-3.0-opus": (0.015, 0.075),
    "claude-3.0-haiku": (0.00025, 0.00125),
}


class AnthropicClient:
    def __init__(self, **kwargs: Any):
        self.load_config(**kwargs)

        # validate the configuration
        assert self._model is not None, "Please provide a `model` in the config_list to use the Anthropic API."

        # check if the api_key is provided in the environment variables
        if not self._api_key:
            self._api_key = os.getenv("ANTHROPIC_API_KEY")
        assert (
            self._api_key is not None
        ), "Please provide an `api_key` in the config_list to use the Anthropic API or set the `ANTHROPIC_API_KEY` environment variable."

    def load_config(self, **kwargs: Any):
        """Load the configuration for the Anthropic API client."""
        if config in kwargs:
            self._config = kwargs.get("config")
        self._model = kwargs.get("model", None)
        self._api_key = kwargs.get("api_key", None)

        self._temperature = kwargs.get("temperature", 0.7)
        if self._temperature is not None and not isinstance(self._temperature, float):
            warnings.warn("Config error: temperature must be a float or None, is default set to 0.7", UserWarning)
            self._temperature = 0.7

        self._max_tokens = kwargs.get("max_tokens", None)
        if self._max_tokens is not None and not isinstance(self._max_tokens, int):
            warnings.warn("Config error: max_tokens must be an int or None", UserWarning)
            self._max_tokens = None

    def cost(self, response: Completion) -> float:
        total = 0.0
        tokens = {
            "input": response.usage.input_tokens if response.usage is not None else 0,
            "output": response.usage.output_tokens if response.usage is not None else 0,
        }

        if self._model in ANTHROPIC_PRICING_1k:
            cost_per_1k = ANTHROPIC_PRICING_1k[self._model]
            total = (tokens["input"] + tokens["output"]) / 1000 * cost_per_1k[0]
        else:
            warnings.warn(f"Cost calculation not available for model {self._model}", UserWarning)

        return total
