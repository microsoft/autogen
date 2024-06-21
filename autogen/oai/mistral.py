"""Create an OpenAI-compatible client using Mistral.AI's API.

Example:
    llm_config={
        "config_list": [{
            "api_type": "mistral",
            "model": "open-mixtral-8x22b",
            "api_key": os.environ.get("MISTRAL_API_KEY")
            }
    ]}

    agent = autogen.AssistantAgent("my_agent", llm_config=llm_config)

Install Mistral.AI python library using: pip install --upgrade mistralai

Resources:
- https://docs.mistral.ai/getting-started/quickstart/
"""

# Important notes when using the Mistral.AI API:
# The first system message can greatly affect whether the model returns a tool call, including text that references the ability to use functions will help.
# Changing the role on the first system message to 'user' improved the chances of the model recommending a tool call.

import inspect
import json
import os
import time
import warnings
from typing import Any, Dict, List, Tuple, Union

# Mistral libraries
# pip install mistralai
from mistralai.client import MistralClient
from mistralai.exceptions import MistralAPIException
from mistralai.models.chat_completion import ChatCompletionResponse, ChatMessage, ToolCall
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage
from typing_extensions import Annotated

from autogen.oai.client_utils import should_hide_tools, validate_parameter


class MistralAIClient:
    """Client for Mistral.AI's API."""

    def __init__(self, **kwargs):
        """Requires api_key or environment variable to be set

        Args:
            api_key (str): The API key for using Mistral.AI (or environment variable MISTRAL_API_KEY needs to be set)
        """
        # Ensure we have the api_key upon instantiation
        self.api_key = kwargs.get("api_key", None)
        if not self.api_key:
            self.api_key = os.getenv("MISTRAL_API_KEY", None)

        assert (
            self.api_key
        ), "Please specify the 'api_key' in your config list entry for Mistral or set the MISTRAL_API_KEY env variable."

    def message_retrieval(self, response: ChatCompletionResponse) -> Union[List[str], List[ChatCompletionMessage]]:
        """Retrieve the messages from the response."""

        return [choice.message for choice in response.choices]

    def cost(self, response) -> float:
        return response.cost

    def parse_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Loads the parameters for Mistral.AI API from the passed in parameters and returns a validated set. Checks types, ranges, and sets defaults"""
        mistral_params = {}

        # 1. Validate models
        mistral_params["model"] = params.get("model", None)
        assert mistral_params[
            "model"
        ], "Please specify the 'model' in your config list entry to nominate the Mistral.ai model to use."

        # 2. Validate allowed Mistral.AI parameters
        mistral_params["temperature"] = validate_parameter(params, "temperature", (int, float), True, 0.7, None, None)
        mistral_params["top_p"] = validate_parameter(params, "top_p", (int, float), True, None, None, None)
        mistral_params["max_tokens"] = validate_parameter(params, "max_tokens", int, True, None, (0, None), None)
        mistral_params["safe_prompt"] = validate_parameter(
            params, "safe_prompt", bool, False, False, None, [True, False]
        )
        mistral_params["random_seed"] = validate_parameter(params, "random_seed", int, True, None, False, None)

        # 3. Convert messages to Mistral format
        mistral_messages = []
        tool_call_ids = {}  # tool call ids to function name mapping
        for message in params["messages"]:
            if message["role"] == "assistant" and "tool_calls" in message and message["tool_calls"] is not None:
                # Convert OAI ToolCall to Mistral ToolCall
                openai_toolcalls = message["tool_calls"]
                mistral_toolcalls = []
                for toolcall in openai_toolcalls:
                    mistral_toolcall = ToolCall(id=toolcall["id"], function=toolcall["function"])
                    mistral_toolcalls.append(mistral_toolcall)
                mistral_messages.append(
                    ChatMessage(role=message["role"], content=message["content"], tool_calls=mistral_toolcalls)
                )

                # Map tool call id to the function name
                for tool_call in message["tool_calls"]:
                    tool_call_ids[tool_call["id"]] = tool_call["function"]["name"]

            elif message["role"] in ("system", "user", "assistant"):
                # Note this ChatMessage can take a 'name' but it is rejected by the Mistral API if not role=tool, so, no, the 'name' field is not used.
                mistral_messages.append(ChatMessage(role=message["role"], content=message["content"]))

            elif message["role"] == "tool":
                # Indicates the result of a tool call, the name is the function name called
                mistral_messages.append(
                    ChatMessage(
                        role="tool",
                        name=tool_call_ids[message["tool_call_id"]],
                        content=message["content"],
                        tool_call_id=message["tool_call_id"],
                    )
                )
            else:
                warnings.warn(f"Unknown message role {message['role']}", UserWarning)

        # If a 'system' message follows an 'assistant' message, change it to 'user'
        # This can occur when using LLM summarisation
        for i in range(1, len(mistral_messages)):
            if mistral_messages[i - 1].role == "assistant" and mistral_messages[i].role == "system":
                mistral_messages[i].role = "user"

        mistral_params["messages"] = mistral_messages

        # 4. Add tools to the call if we have them and aren't hiding them
        if "tools" in params:
            hide_tools = validate_parameter(
                params, "hide_tools", str, False, "never", None, ["if_all_run", "if_any_run", "never"]
            )
            if not should_hide_tools(params["messages"], params["tools"], hide_tools):
                mistral_params["tools"] = params["tools"]
        return mistral_params

    def create(self, params: Dict[str, Any]) -> ChatCompletion:
        # 1. Parse parameters to Mistral.AI API's parameters
        mistral_params = self.parse_params(params)

        # 2. Call Mistral.AI API
        client = MistralClient(api_key=self.api_key)
        mistral_response = client.chat(**mistral_params)
        # TODO: Handle streaming

        # 3. Convert Mistral response to OAI compatible format
        if mistral_response.choices[0].finish_reason == "tool_calls":
            mistral_finish = "tool_calls"
            tool_calls = []
            for tool_call in mistral_response.choices[0].message.tool_calls:
                tool_calls.append(
                    ChatCompletionMessageToolCall(
                        id=tool_call.id,
                        function={"name": tool_call.function.name, "arguments": tool_call.function.arguments},
                        type="function",
                    )
                )
        else:
            mistral_finish = "stop"
            tool_calls = None

        message = ChatCompletionMessage(
            role="assistant",
            content=mistral_response.choices[0].message.content,
            function_call=None,
            tool_calls=tool_calls,
        )
        choices = [Choice(finish_reason=mistral_finish, index=0, message=message)]

        response_oai = ChatCompletion(
            id=mistral_response.id,
            model=mistral_response.model,
            created=int(time.time()),
            object="chat.completion",
            choices=choices,
            usage=CompletionUsage(
                prompt_tokens=mistral_response.usage.prompt_tokens,
                completion_tokens=mistral_response.usage.completion_tokens,
                total_tokens=mistral_response.usage.prompt_tokens + mistral_response.usage.completion_tokens,
            ),
            cost=calculate_mistral_cost(
                mistral_response.usage.prompt_tokens, mistral_response.usage.completion_tokens, mistral_response.model
            ),
        )

        return response_oai

    @staticmethod
    def get_usage(response: ChatCompletionResponse) -> Dict:
        return {
            "prompt_tokens": response.usage.prompt_tokens if response.usage is not None else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage is not None else 0,
            "total_tokens": (
                response.usage.prompt_tokens + response.usage.completion_tokens if response.usage is not None else 0
            ),
            "cost": response.cost if hasattr(response, "cost") else 0,
            "model": response.model,
        }


def calculate_mistral_cost(input_tokens: int, output_tokens: int, model_name: str) -> float:
    """Calculate the cost of the mistral response."""

    # Prices per 1 million tokens
    # https://mistral.ai/technology/
    model_cost_map = {
        "open-mistral-7b": {"input": 0.25, "output": 0.25},
        "open-mixtral-8x7b": {"input": 0.7, "output": 0.7},
        "open-mixtral-8x22b": {"input": 2.0, "output": 6.0},
        "mistral-small-latest": {"input": 1.0, "output": 3.0},
        "mistral-medium-latest": {"input": 2.7, "output": 8.1},
        "mistral-large-latest": {"input": 4.0, "output": 12.0},
    }

    # Ensure we have the model they are using and return the total cost
    if model_name in model_cost_map:
        costs = model_cost_map[model_name]

        return (input_tokens * costs["input"] / 1_000_000) + (output_tokens * costs["output"] / 1_000_000)
    else:
        warnings.warn(f"Cost calculation is not implemented for model {model_name}, will return $0.", UserWarning)
        return 0
