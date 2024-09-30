"""Create an OpenAI-compatible client using Cerebras's API.

Example:
    llm_config={
        "config_list": [{
            "api_type": "cerebras",
            "model": "llama3.1-8b",
            "api_key": os.environ.get("CEREBRAS_API_KEY")
        }]
    }

    agent = autogen.AssistantAgent("my_agent", llm_config=llm_config)

Install Cerebras's python library using: pip install --upgrade cerebras_cloud_sdk

Resources:
- https://inference-docs.cerebras.ai/quickstart
"""

from __future__ import annotations

import copy
import os
import time
import warnings
from typing import Any, Dict, List

from cerebras.cloud.sdk import Cerebras, Stream
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage

from autogen.oai.client_utils import should_hide_tools, validate_parameter

CEREBRAS_PRICING_1K = {
    # Convert pricing per million to per thousand tokens.
    "llama3.1-8b": (0.10 / 1000, 0.10 / 1000),
    "llama3.1-70b": (0.60 / 1000, 0.60 / 1000),
}


class CerebrasClient:
    """Client for Cerebras's API."""

    def __init__(self, api_key=None, **kwargs):
        """Requires api_key or environment variable to be set

        Args:
            api_key (str): The API key for using Cerebras (or environment variable CEREBRAS_API_KEY needs to be set)
        """
        # Ensure we have the api_key upon instantiation
        self.api_key = api_key
        if not self.api_key:
            self.api_key = os.getenv("CEREBRAS_API_KEY")

        assert (
            self.api_key
        ), "Please include the api_key in your config list entry for Cerebras or set the CEREBRAS_API_KEY env variable."

    def message_retrieval(self, response: ChatCompletion) -> List:
        """
        Retrieve and return a list of strings or a list of Choice.Message from the response.

        NOTE: if a list of Choice.Message is returned, it currently needs to contain the fields of OpenAI's ChatCompletion Message object,
        since that is expected for function or tool calling in the rest of the codebase at the moment, unless a custom agent is being used.
        """
        return [choice.message for choice in response.choices]

    def cost(self, response: ChatCompletion) -> float:
        # Note: This field isn't explicitly in `ChatCompletion`, but is injected during chat creation.
        return response.cost

    @staticmethod
    def get_usage(response: ChatCompletion) -> Dict:
        """Return usage summary of the response using RESPONSE_USAGE_KEYS."""
        # ...  # pragma: no cover
        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cost": response.cost,
            "model": response.model,
        }

    def parse_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Loads the parameters for Cerebras API from the passed in parameters and returns a validated set. Checks types, ranges, and sets defaults"""
        cerebras_params = {}

        # Check that we have what we need to use Cerebras's API
        # We won't enforce the available models as they are likely to change
        cerebras_params["model"] = params.get("model", None)
        assert cerebras_params[
            "model"
        ], "Please specify the 'model' in your config list entry to nominate the Cerebras model to use."

        # Validate allowed Cerebras parameters
        # https://inference-docs.cerebras.ai/api-reference/chat-completions
        cerebras_params["max_tokens"] = validate_parameter(params, "max_tokens", int, True, None, (0, None), None)
        cerebras_params["seed"] = validate_parameter(params, "seed", int, True, None, None, None)
        cerebras_params["stream"] = validate_parameter(params, "stream", bool, True, False, None, None)
        cerebras_params["temperature"] = validate_parameter(
            params, "temperature", (int, float), True, 1, (0, 1.5), None
        )
        cerebras_params["top_p"] = validate_parameter(params, "top_p", (int, float), True, None, None, None)

        return cerebras_params

    def create(self, params: Dict) -> ChatCompletion:

        messages = params.get("messages", [])

        # Convert AutoGen messages to Cerebras messages
        cerebras_messages = oai_messages_to_cerebras_messages(messages)

        # Parse parameters to the Cerebras API's parameters
        cerebras_params = self.parse_params(params)

        # Add tools to the call if we have them and aren't hiding them
        if "tools" in params:
            hide_tools = validate_parameter(
                params, "hide_tools", str, False, "never", None, ["if_all_run", "if_any_run", "never"]
            )
            if not should_hide_tools(cerebras_messages, params["tools"], hide_tools):
                cerebras_params["tools"] = params["tools"]

        cerebras_params["messages"] = cerebras_messages

        # We use chat model by default, and set max_retries to 5 (in line with typical retries loop)
        client = Cerebras(api_key=self.api_key, max_retries=5)

        # Token counts will be returned
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        # Streaming tool call recommendations
        streaming_tool_calls = []

        ans = None
        try:
            response = client.chat.completions.create(**cerebras_params)
        except Exception as e:
            raise RuntimeError(f"Cerebras exception occurred: {e}")
        else:

            if cerebras_params["stream"]:
                # Read in the chunks as they stream, taking in tool_calls which may be across
                # multiple chunks if more than one suggested
                ans = ""
                for chunk in response:
                    # Grab first choice, which _should_ always be generated.
                    ans = ans + (chunk.choices[0].delta.content or "")

                    if chunk.choices[0].delta.tool_calls:
                        # We have a tool call recommendation
                        for tool_call in chunk.choices[0].delta.tool_calls:
                            streaming_tool_calls.append(
                                ChatCompletionMessageToolCall(
                                    id=tool_call.id,
                                    function={
                                        "name": tool_call.function.name,
                                        "arguments": tool_call.function.arguments,
                                    },
                                    type="function",
                                )
                            )

                    if chunk.choices[0].finish_reason:
                        prompt_tokens = chunk.x_cerebras.usage.prompt_tokens
                        completion_tokens = chunk.x_cerebras.usage.completion_tokens
                        total_tokens = chunk.x_cerebras.usage.total_tokens
            else:
                # Non-streaming finished
                ans: str = response.choices[0].message.content

                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens

        if response is not None:
            if isinstance(response, Stream):
                # Streaming response
                if chunk.choices[0].finish_reason == "tool_calls":
                    cerebras_finish = "tool_calls"
                    tool_calls = streaming_tool_calls
                else:
                    cerebras_finish = "stop"
                    tool_calls = None

                response_content = ans
                response_id = chunk.id
            else:
                # Non-streaming response
                # If we have tool calls as the response, populate completed tool calls for our return OAI response
                if response.choices[0].finish_reason == "tool_calls":
                    cerebras_finish = "tool_calls"
                    tool_calls = []
                    for tool_call in response.choices[0].message.tool_calls:
                        tool_calls.append(
                            ChatCompletionMessageToolCall(
                                id=tool_call.id,
                                function={"name": tool_call.function.name, "arguments": tool_call.function.arguments},
                                type="function",
                            )
                        )
                else:
                    cerebras_finish = "stop"
                    tool_calls = None

                response_content = response.choices[0].message.content
                response_id = response.id
        else:
            raise RuntimeError("Failed to get response from Cerebras after retrying 5 times.")

        # 3. convert output
        message = ChatCompletionMessage(
            role="assistant",
            content=response_content,
            function_call=None,
            tool_calls=tool_calls,
        )
        choices = [Choice(finish_reason=cerebras_finish, index=0, message=message)]

        response_oai = ChatCompletion(
            id=response_id,
            model=cerebras_params["model"],
            created=int(time.time()),
            object="chat.completion",
            choices=choices,
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            # Note: This seems to be a field that isn't in the schema of `ChatCompletion`, so Pydantic
            #       just adds it dynamically.
            cost=calculate_cerebras_cost(prompt_tokens, completion_tokens, cerebras_params["model"]),
        )

        return response_oai


def oai_messages_to_cerebras_messages(messages: list[Dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert messages from OAI format to Cerebras's format.
    We correct for any specific role orders and types.
    """

    cerebras_messages = copy.deepcopy(messages)

    # Remove the name field
    for message in cerebras_messages:
        if "name" in message:
            message.pop("name", None)

    return cerebras_messages


def calculate_cerebras_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calculate the cost of the completion using the Cerebras pricing."""
    total = 0.0

    if model in CEREBRAS_PRICING_1K:
        input_cost_per_k, output_cost_per_k = CEREBRAS_PRICING_1K[model]
        input_cost = (input_tokens / 1000) * input_cost_per_k
        output_cost = (output_tokens / 1000) * output_cost_per_k
        total = input_cost + output_cost
    else:
        warnings.warn(f"Cost calculation not available for model {model}", UserWarning)

    return total
