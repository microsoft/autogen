"""
Create an OpenAI-compatible client for the Anthropic API.

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

Example usage for Anthropic Bedrock:

Install the `anthropic` package by running `pip install --upgrade anthropic`.
- https://docs.anthropic.com/en/docs/quickstart-guide

import autogen

config_list = [
    {
        "model": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "aws_access_key":<accessKey>,
        "aws_secret_key":<secretKey>,
        "aws_session_token":<sessionTok>,
        "aws_region":"us-east-1",
        "api_type": "anthropic",
    }
]

assistant = autogen.AssistantAgent("assistant", llm_config={"config_list": config_list})

"""

from __future__ import annotations

import copy
import inspect
import json
import os
import time
import warnings
from typing import Any, Dict, List, Tuple, Union

from anthropic import Anthropic, AnthropicBedrock
from anthropic import __version__ as anthropic_version
from anthropic.types import Completion, Message, TextBlock, ToolUseBlock
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage
from typing_extensions import Annotated

from autogen.oai.client_utils import validate_parameter

TOOL_ENABLED = anthropic_version >= "0.23.1"
if TOOL_ENABLED:
    from anthropic.types.tool_use_block_param import (
        ToolUseBlockParam,
    )


ANTHROPIC_PRICING_1k = {
    "claude-3-5-sonnet-20240620": (0.003, 0.015),
    "claude-3-sonnet-20240229": (0.003, 0.015),
    "claude-3-opus-20240229": (0.015, 0.075),
    "claude-3-haiku-20240307": (0.00025, 0.00125),
    "claude-2.1": (0.008, 0.024),
    "claude-2.0": (0.008, 0.024),
    "claude-instant-1.2": (0.008, 0.024),
}


class AnthropicClient:
    def __init__(self, **kwargs: Any):
        """
        Initialize the Anthropic API client.
        Args:
            api_key (str): The API key for the Anthropic API or set the `ANTHROPIC_API_KEY` environment variable.
        """
        self._api_key = kwargs.get("api_key", None)
        self._aws_access_key = kwargs.get("aws_access_key", None)
        self._aws_secret_key = kwargs.get("aws_secret_key", None)
        self._aws_session_token = kwargs.get("aws_session_token", None)
        self._aws_region = kwargs.get("aws_region", None)

        if not self._api_key:
            self._api_key = os.getenv("ANTHROPIC_API_KEY")

        if not self._aws_access_key:
            self._aws_access_key = os.getenv("AWS_ACCESS_KEY")

        if not self._aws_secret_key:
            self._aws_secret_key = os.getenv("AWS_SECRET_KEY")

        if not self._aws_region:
            self._aws_region = os.getenv("AWS_REGION")

        if self._api_key is None and (
            self._aws_access_key is None or self._aws_secret_key is None or self._aws_region is None
        ):
            raise ValueError("API key or AWS credentials are required to use the Anthropic API.")

        if self._api_key is not None:
            self._client = Anthropic(api_key=self._api_key)
        else:
            self._client = AnthropicBedrock(
                aws_access_key=self._aws_access_key,
                aws_secret_key=self._aws_secret_key,
                aws_session_token=self._aws_session_token,
                aws_region=self._aws_region,
            )

        self._last_tooluse_status = {}

    def load_config(self, params: Dict[str, Any]):
        """Load the configuration for the Anthropic API client."""
        anthropic_params = {}

        anthropic_params["model"] = params.get("model", None)
        assert anthropic_params["model"], "Please provide a `model` in the config_list to use the Anthropic API."

        anthropic_params["temperature"] = validate_parameter(
            params, "temperature", (float, int), False, 1.0, (0.0, 1.0), None
        )
        anthropic_params["max_tokens"] = validate_parameter(params, "max_tokens", int, False, 4096, (1, None), None)
        anthropic_params["top_k"] = validate_parameter(params, "top_k", int, True, None, (1, None), None)
        anthropic_params["top_p"] = validate_parameter(params, "top_p", (float, int), True, None, (0.0, 1.0), None)
        anthropic_params["stop_sequences"] = validate_parameter(params, "stop_sequences", list, True, None, None, None)
        anthropic_params["stream"] = validate_parameter(params, "stream", bool, False, False, None, None)

        if anthropic_params["stream"]:
            warnings.warn(
                "Streaming is not currently supported, streaming will be disabled.",
                UserWarning,
            )
            anthropic_params["stream"] = False

        return anthropic_params

    def cost(self, response) -> float:
        """Calculate the cost of the completion using the Anthropic pricing."""
        return response.cost

    @property
    def api_key(self):
        return self._api_key

    @property
    def aws_access_key(self):
        return self._aws_access_key

    @property
    def aws_secret_key(self):
        return self._aws_secret_key

    @property
    def aws_session_token(self):
        return self._aws_session_token

    @property
    def aws_region(self):
        return self._aws_region

    def create(self, params: Dict[str, Any]) -> Completion:
        if "tools" in params:
            converted_functions = self.convert_tools_to_functions(params["tools"])
            params["functions"] = params.get("functions", []) + converted_functions

        # Convert AutoGen messages to Anthropic messages
        anthropic_messages = oai_messages_to_anthropic_messages(params)
        anthropic_params = self.load_config(params)

        # TODO: support stream
        params = params.copy()
        if "functions" in params:
            tools_configs = params.pop("functions")
            tools_configs = [self.openai_func_to_anthropic(tool) for tool in tools_configs]
            params["tools"] = tools_configs

        # Anthropic doesn't accept None values, so we need to use keyword argument unpacking instead of setting parameters.
        # Copy params we need into anthropic_params
        # Remove any that don't have values
        anthropic_params["messages"] = anthropic_messages
        if "system" in params:
            anthropic_params["system"] = params["system"]
        if "tools" in params:
            anthropic_params["tools"] = params["tools"]
        if anthropic_params["top_k"] is None:
            del anthropic_params["top_k"]
        if anthropic_params["top_p"] is None:
            del anthropic_params["top_p"]
        if anthropic_params["stop_sequences"] is None:
            del anthropic_params["stop_sequences"]

        response = self._client.messages.create(**anthropic_params)

        # Calculate and save the cost onto the response
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens

        message_text = ""
        if response is not None:
            # If we have tool use as the response, populate completed tool calls for our return OAI response
            if response.stop_reason == "tool_use":
                anthropic_finish = "tool_calls"
                tool_calls = []
                for content in response.content:
                    if type(content) == ToolUseBlock:
                        tool_calls.append(
                            ChatCompletionMessageToolCall(
                                id=content.id,
                                function={"name": content.name, "arguments": json.dumps(content.input)},
                                type="function",
                            )
                        )
            else:
                anthropic_finish = "stop"
                tool_calls = None

            # Retrieve any text content from the response
            for content in response.content:
                if type(content) == TextBlock:
                    message_text = content.text
                    break

        # Convert output back to AutoGen response format
        message = ChatCompletionMessage(
            role="assistant",
            content=message_text,
            function_call=None,
            tool_calls=tool_calls,
        )
        choices = [Choice(finish_reason=anthropic_finish, index=0, message=message)]

        response_oai = ChatCompletion(
            id=response.id,
            model=anthropic_params["model"],
            created=int(time.time()),
            object="chat.completion",
            choices=choices,
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            cost=_calculate_cost(prompt_tokens, completion_tokens, anthropic_params["model"]),
        )

        return response_oai

    def message_retrieval(self, response) -> List:
        """
        Retrieve and return a list of strings or a list of Choice.Message from the response.

        NOTE: if a list of Choice.Message is returned, it currently needs to contain the fields of OpenAI's ChatCompletion Message object,
        since that is expected for function or tool calling in the rest of the codebase at the moment, unless a custom agent is being used.
        """
        return [choice.message for choice in response.choices]

    @staticmethod
    def openai_func_to_anthropic(openai_func: dict) -> dict:
        res = openai_func.copy()
        res["input_schema"] = res.pop("parameters")
        return res

    @staticmethod
    def get_usage(response: ChatCompletion) -> Dict:
        """Get the usage of tokens and their cost information."""
        return {
            "prompt_tokens": response.usage.prompt_tokens if response.usage is not None else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage is not None else 0,
            "total_tokens": response.usage.total_tokens if response.usage is not None else 0,
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


def oai_messages_to_anthropic_messages(params: Dict[str, Any]) -> list[dict[str, Any]]:
    """Convert messages from OAI format to Anthropic format.
    We correct for any specific role orders and types, etc.
    """

    # Track whether we have tools passed in. If not,  tool use / result messages should be converted to text messages.
    # Anthropic requires a tools parameter with the tools listed, if there are other messages with tool use or tool results.
    # This can occur when we don't need tool calling, such as for group chat speaker selection.
    has_tools = "tools" in params

    # Convert messages to Anthropic compliant format
    processed_messages = []

    # Used to interweave user messages to ensure user/assistant alternating
    user_continue_message = {"content": "Please continue.", "role": "user"}
    assistant_continue_message = {"content": "Please continue.", "role": "assistant"}

    tool_use_messages = 0
    tool_result_messages = 0
    last_tool_use_index = -1
    last_tool_result_index = -1
    for message in params["messages"]:
        if message["role"] == "system":
            params["system"] = params.get("system", "") + (" " if "system" in params else "") + message["content"]
        else:
            # New messages will be added here, manage role alternations
            expected_role = "user" if len(processed_messages) % 2 == 0 else "assistant"

            if "tool_calls" in message:
                # Map the tool call options to Anthropic's ToolUseBlock
                tool_uses = []
                tool_names = []
                for tool_call in message["tool_calls"]:
                    tool_uses.append(
                        ToolUseBlock(
                            type="tool_use",
                            id=tool_call["id"],
                            name=tool_call["function"]["name"],
                            input=json.loads(tool_call["function"]["arguments"]),
                        )
                    )
                    if has_tools:
                        tool_use_messages += 1
                    tool_names.append(tool_call["function"]["name"])

                if expected_role == "user":
                    # Insert an extra user message as we will append an assistant message
                    processed_messages.append(user_continue_message)

                if has_tools:
                    processed_messages.append({"role": "assistant", "content": tool_uses})
                    last_tool_use_index = len(processed_messages) - 1
                else:
                    # Not using tools, so put in a plain text message
                    processed_messages.append(
                        {
                            "role": "assistant",
                            "content": f"Some internal function(s) that could be used: [{', '.join(tool_names)}]",
                        }
                    )
            elif "tool_call_id" in message:
                if has_tools:
                    # Map the tool usage call to tool_result for Anthropic
                    tool_result = {
                        "type": "tool_result",
                        "tool_use_id": message["tool_call_id"],
                        "content": message["content"],
                    }

                    # If the previous message also had a tool_result, add it to that
                    # Otherwise append a new message
                    if last_tool_result_index == len(processed_messages) - 1:
                        processed_messages[-1]["content"].append(tool_result)
                    else:
                        if expected_role == "assistant":
                            # Insert an extra assistant message as we will append a user message
                            processed_messages.append(assistant_continue_message)

                        processed_messages.append({"role": "user", "content": [tool_result]})
                        last_tool_result_index = len(processed_messages) - 1

                    tool_result_messages += 1
                else:
                    # Not using tools, so put in a plain text message
                    processed_messages.append(
                        {"role": "user", "content": f"Running the function returned: {message['content']}"}
                    )
            elif message["content"] == "":
                # Ignoring empty messages
                pass
            else:
                if expected_role != message["role"]:
                    # Inserting the alternating continue message
                    processed_messages.append(
                        user_continue_message if expected_role == "user" else assistant_continue_message
                    )

                processed_messages.append(message)

    # We'll replace the last tool_use if there's no tool_result (occurs if we finish the conversation before running the function)
    if has_tools and tool_use_messages != tool_result_messages:
        processed_messages[last_tool_use_index] = assistant_continue_message

    # name is not a valid field on messages
    for message in processed_messages:
        if "name" in message:
            message.pop("name", None)

    # Note: When using reflection_with_llm we may end up with an "assistant" message as the last message and that may cause a blank response
    # So, if the last role is not user, add a 'user' continue message at the end
    if processed_messages[-1]["role"] != "user":
        processed_messages.append(user_continue_message)

    return processed_messages


def _calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calculate the cost of the completion using the Anthropic pricing."""
    total = 0.0

    if model in ANTHROPIC_PRICING_1k:
        input_cost_per_1k, output_cost_per_1k = ANTHROPIC_PRICING_1k[model]
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        total = input_cost + output_cost
    else:
        warnings.warn(f"Cost calculation not available for model {model}", UserWarning)

    return total
