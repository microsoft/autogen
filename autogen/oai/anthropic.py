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

assistant = autogen.AssistantAgent("assistant", llm_config={"config_list": config_list})
"""

from __future__ import annotations

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
    from anthropic.types.tool_use_block_param import (
        ToolUseBlockParam,
    )


ANTHROPIC_PRICING_1k = {
    "claude-3-sonnet-20240229": (0.003, 0.015),
    "claude-3-opus-20240229": (0.015, 0.075),
    "claude-2.0": (0.008, 0.024),
    "claude-2.1": (0.008, 0.024),
    "claude-3.0-opus": (0.015, 0.075),
    "claude-3.0-haiku": (0.00025, 0.00125),
}


class AnthropicClient:
    def __init__(self, **kwargs: Any):
        """
        Initialize the Anthropic API client.
        Args:
            api_key (str): The API key for the Anthropic API or set the `ANTHROPIC_API_KEY` environment variable.
        """
        self._api_key = kwargs.get("api_key", None)

        if not self._api_key:
            self._api_key = os.getenv("ANTHROPIC_API_KEY")

        if self._api_key is None:
            raise ValueError("API key is required to use the Anthropic API.")

        self._client = Anthropic(api_key=self._api_key)
        self._last_tooluse_status = {}

    def load_config(self, params: Dict[str, Any]):
        """Load the configuration for the Anthropic API client."""
        anthropic_params = {}

        anthropic_params["model"] = params.get("model", None)
        assert anthropic_params["model"], "Please provide a `model` in the config_list to use the Anthropic API."

        anthropic_params["stream"] = params.get("stream", False)
        if not isinstance(anthropic_params["stream"], bool):
            warnings.warn("Config error: stream must be a bool, defaulting to False", UserWarning)
            anthropic_params["stream"] = False

        anthropic_params["temperature"] = params.get("temperature", 0.7)
        if anthropic_params["temperature"] is not None and not isinstance(anthropic_params["temperature"], float):
            warnings.warn("Config error: temperature must be a float or None, defaulting to 0.7", UserWarning)
            anthropic_params["temperature"] = 0.7  # Ensure the default is set

        anthropic_params["max_tokens"] = params.get("max_tokens", None)
        if anthropic_params["max_tokens"] is not None and not isinstance(anthropic_params["max_tokens"], int):
            warnings.warn("Config error: max_tokens must be an int or None", UserWarning)
            anthropic_params["max_tokens"] = None

        # Update stop_sequences with validation
        anthropic_params["stop_sequences"] = params.get("stop_sequences", None)
        if anthropic_params["stop_sequences"] is not None and not isinstance(anthropic_params["stop_sequences"], list):
            warnings.warn("Config error: stop_sequences must be a list or None", UserWarning)
            anthropic_params["stop_sequences"] = None

        # Update top_k with validation
        anthropic_params["top_k"] = params.get("top_k", None)
        if anthropic_params["top_k"] is not None and not isinstance(anthropic_params["top_k"], int):
            warnings.warn("Config error: top_k must be an int or None", UserWarning)
            anthropic_params["top_k"] = None

        # Update top_p with validation
        anthropic_params["top_p"] = params.get("top_p", None)
        if anthropic_params["top_p"] is not None and not isinstance(anthropic_params["top_p"], float):
            warnings.warn("Config error: top_p must be a float or None", UserWarning)
            anthropic_params["top_p"] = None

        return anthropic_params

    def cost(self, response: Message) -> float:
        """Calculate the cost of the completion using the Anthropic pricing."""
        return self._calculate_cost(response)

    @property
    def api_key(self):
        return self._api_key

    def create(self, params: Dict[str, Any]) -> Completion:
        """Create a completion for a given config.

        Args:
            params: The params for the completion.

        Returns:
            The completion.
        """
        if "tools" in params:
            converted_functions = self.convert_tools_to_functions(params["tools"])
            params["functions"] = params.get("functions", []) + converted_functions

        raw_contents = params["messages"]
        anthropic_params = self.load_config(params)

        processed_messages = []
        for message in raw_contents:

            if message["role"] == "system":
                params["system"] = message["content"]
            elif message["role"] == "function":
                processed_messages.append(self.return_function_call_result(message["content"]))
            elif "function_call" in message:
                processed_messages.append(self.restore_last_tooluse_status())
            elif message["content"] == "":
                message["content"] = "I'm done. Please send TERMINATE"
                processed_messages.append(message)
            else:
                processed_messages.append(message)

        params["messages"] = processed_messages

        completions: Completion = self._client.messages  # type: ignore [attr-defined]

        # TODO: support stream
        params = params.copy()
        params["stream"] = False
        params["max_tokens"] = params.get("max_tokens", 4096)
        if "functions" in params:
            tools_configs = params.pop("functions")
            tools_configs = [self.openai_func_to_anthropic(tool) for tool in tools_configs]
            params["tools"] = tools_configs

        response = completions.create(
            model=anthropic_params["model"],
            tools=params["tools"],
            tool_choice="auto",
            messages=params["messages"],
            temperature=anthropic_params["temperature"],
            max_tokens=anthropic_params["max_tokens"],
            stop_sequences=anthropic_params["stop_sequences"],
            top_k=anthropic_params["top_k"],
            top_p=anthropic_params["top_p"],
        )

        return response

    def message_retrieval(self, response: Union[Message]) -> Union[List[str], List[ChatCompletionMessage]]:
        """Retrieve the messages from the response."""
        messages = response.content
        if len(messages) == 0:
            return [None]
        res = []
        if TOOL_ENABLED:
            for choice in messages:
                if choice.type == "tool_use":
                    res.insert(0, self.response_to_openai_message(choice))
                    self._last_tooluse_status["tool_use"] = choice.model_dump()
                else:
                    res.append(choice.text)
                    self._last_tooluse_status["think"] = choice.text

            return res

        else:
            return [  # type: ignore [return-value]
                choice.text if choice.message.function_call is not None else choice.message.content  # type: ignore [union-attr]
                for choice in messages
            ]

    def response_to_openai_message(self, response) -> ChatCompletionMessage:
        dict_response = response.model_dump()
        return ChatCompletionMessage(
            content=None,
            role="assistant",
            function_call={"name": dict_response["name"], "arguments": json.dumps(dict_response["input"])},
        )

    def restore_last_tooluse_status(self) -> Dict:
        cached_content = []
        if "think" in self._last_tooluse_status:
            cached_content.append({"type": "text", "text": self._last_tooluse_status["think"]})
        cached_content.append(self._last_tooluse_status["tool_use"])
        res = {"role": "assistant", "content": cached_content}
        return res

    def return_function_call_result(self, result: str) -> Dict:
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": self._last_tooluse_status["tool_use"]["id"],
                    "content": result,
                }
            ],
        }

    @staticmethod
    def openai_func_to_anthropic(openai_func: dict) -> dict:
        res = openai_func.copy()
        res["input_schema"] = res.pop("parameters")
        return res

    @staticmethod
    def get_usage(response: Message) -> Dict:
        return {
            "prompt_tokens": response.usage.input_tokens if response.usage is not None else 0,
            "completion_tokens": response.usage.output_tokens if response.usage is not None else 0,
            "total_tokens": (
                response.usage.input_tokens + response.usage.output_tokens if response.usage is not None else 0
            ),
            "cost": response.cost if hasattr(response, "cost") else 0.0,
            "model": response.model,
        }

    @staticmethod
    def convert_tools_to_functions(tools: List) -> List:
        functions = []
        for tool in tools:
            if tool.get("type") == "function" and "function" in tool:
                functions.append(tool["function"])

        return functions

    def _calculate_cost(self, response: Message) -> float:
        """Calculate the cost of the completion using the Anthropic pricing."""
        total = 0.0
        tokens = {
            "input": response.usage.input_tokens if response.usage is not None else 0,
            "output": response.usage.output_tokens if response.usage is not None else 0,
        }

        if self._model in ANTHROPIC_PRICING_1k:
            input_cost_per_1k, output_cost_per_1k = ANTHROPIC_PRICING_1k[self._model]
            input_cost = (tokens["input"] / 1000) * input_cost_per_1k
            output_cost = (tokens["output"] / 1000) * output_cost_per_1k
            total = input_cost + output_cost
        else:
            warnings.warn(f"Cost calculation not available for model {self._model}", UserWarning)

        return total
