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

        self._client = Anthropic(model=self._model, api_key=self._api_key)

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
        """Calculate the cost of the completion using the Anthropic pricing."""
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
        processed_messages = []
        for message in raw_contents:

            if message["role"] == "system":
                params["system"] = message["content"]
            elif message["role"] == "function":
                processed_messages.append(self.return_function_call_result(message["content"]))
            elif "function_call" in message:
                processed_messages.append(self.restore_last_tooluse_status())
            elif message["content"] == "":
                # I'm not sure how to elegantly terminate the conversation, please give me some advice about this.
                message["content"] = "I'm done. Please send TERMINATE"
                processed_messages.append(message)
            else:
                processed_messages.append(message)

        params["messages"] = processed_messages

        if TOOL_ENABLED and "functions" in params:
            completions: Completion = self._client.beta.tools.messages
        else:
            completions: Completion = self._client.messages  # type: ignore [attr-defined]

        #TODO: support stream
        params = params.copy()
        params["stream"] = False
        params.pop("model_client_cls")
        params["max_tokens"] = params.get("max_tokens", 4096)
        if "functions" in params:
            tools_configs = params.pop("functions")
            tools_configs = [self.openai_func_to_anthropic(tool) for tool in tools_configs]
            params["tools"] = tools_configs
        response = completions.create(**params)

        return response
    
    def message_retrieval(
        self, response: Union[Message, ToolsBetaMessage]
    ) -> Union[List[str], List[ChatCompletionMessage]]:
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
    def get_usage(response: Completion) -> Dict:
        return {
            "prompt_tokens": response.usage.input_tokens if response.usage is not None else 0,
            "completion_tokens": response.usage.output_tokens if response.usage is not None else 0,
            "total_tokens": (
                response.usage.input_tokens + response.usage.output_tokens if response.usage is not None else 0
            ),
            "cost": response.cost if hasattr(response, "cost") else 0,
            "model": response.model,
        }

    @staticmethod
    def convert_tools_to_functions(tools: List) -> List:
        functions = []
        for tool in tools:
            if tool.get("type") == "function" and "function" in tool:
                functions.append(tool["function"])

        return functions