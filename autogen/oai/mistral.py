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

NOTE: Requires mistralai package version >= 1.0.1
"""

import inspect
import json
import os
import time
import warnings
from typing import Any, Dict, List, Union

# Mistral libraries
# pip install mistralai
from mistralai import (
    AssistantMessage,
    Function,
    FunctionCall,
    Mistral,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage

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

        self._client = Mistral(api_key=self.api_key)

    def message_retrieval(self, response: ChatCompletion) -> Union[List[str], List[ChatCompletionMessage]]:
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

        # TODO
        if params.get("stream", False):
            warnings.warn(
                "Streaming is not currently supported, streaming will be disabled.",
                UserWarning,
            )

        # 3. Convert messages to Mistral format
        mistral_messages = []
        tool_call_ids = {}  # tool call ids to function name mapping
        for message in params["messages"]:
            if message["role"] == "assistant" and "tool_calls" in message and message["tool_calls"] is not None:
                # Convert OAI ToolCall to Mistral ToolCall
                mistral_messages_tools = []
                for toolcall in message["tool_calls"]:
                    mistral_messages_tools.append(
                        ToolCall(
                            id=toolcall["id"],
                            function=FunctionCall(
                                name=toolcall["function"]["name"],
                                arguments=json.loads(toolcall["function"]["arguments"]),
                            ),
                        )
                    )

                mistral_messages.append(AssistantMessage(content="", tool_calls=mistral_messages_tools))

                # Map tool call id to the function name
                for tool_call in message["tool_calls"]:
                    tool_call_ids[tool_call["id"]] = tool_call["function"]["name"]

            elif message["role"] == "system":
                if len(mistral_messages) > 0 and mistral_messages[-1].role == "assistant":
                    # System messages can't appear after an Assistant message, so use a UserMessage
                    mistral_messages.append(UserMessage(content=message["content"]))
                else:
                    mistral_messages.append(SystemMessage(content=message["content"]))
            elif message["role"] == "assistant":
                mistral_messages.append(AssistantMessage(content=message["content"]))
            elif message["role"] == "user":
                mistral_messages.append(UserMessage(content=message["content"]))

            elif message["role"] == "tool":
                # Indicates the result of a tool call, the name is the function name called
                mistral_messages.append(
                    ToolMessage(
                        name=tool_call_ids[message["tool_call_id"]],
                        content=message["content"],
                        tool_call_id=message["tool_call_id"],
                    )
                )
            else:
                warnings.warn(f"Unknown message role {message['role']}", UserWarning)

        # 4. Last message needs to be user or tool, if not, add a "please continue" message
        if not isinstance(mistral_messages[-1], UserMessage) and not isinstance(mistral_messages[-1], ToolMessage):
            mistral_messages.append(UserMessage(content="Please continue."))

        mistral_params["messages"] = mistral_messages

        # 5. Add tools to the call if we have them and aren't hiding them
        if "tools" in params:
            hide_tools = validate_parameter(
                params, "hide_tools", str, False, "never", None, ["if_all_run", "if_any_run", "never"]
            )
            if not should_hide_tools(params["messages"], params["tools"], hide_tools):
                mistral_params["tools"] = tool_def_to_mistral(params["tools"])

        return mistral_params

    def create(self, params: Dict[str, Any]) -> ChatCompletion:
        # 1. Parse parameters to Mistral.AI API's parameters
        mistral_params = self.parse_params(params)

        # 2. Call Mistral.AI API
        mistral_response = self._client.chat.complete(**mistral_params)
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
    def get_usage(response: ChatCompletion) -> Dict:
        return {
            "prompt_tokens": response.usage.prompt_tokens if response.usage is not None else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage is not None else 0,
            "total_tokens": (
                response.usage.prompt_tokens + response.usage.completion_tokens if response.usage is not None else 0
            ),
            "cost": response.cost if hasattr(response, "cost") else 0,
            "model": response.model,
        }


def tool_def_to_mistral(tool_definitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Converts AutoGen tool definition to a mistral tool format"""

    mistral_tools = []

    for autogen_tool in tool_definitions:
        mistral_tool = {
            "type": "function",
            "function": Function(
                name=autogen_tool["function"]["name"],
                description=autogen_tool["function"]["description"],
                parameters=autogen_tool["function"]["parameters"],
            ),
        }

        mistral_tools.append(mistral_tool)

    return mistral_tools


def calculate_mistral_cost(input_tokens: int, output_tokens: int, model_name: str) -> float:
    """Calculate the cost of the mistral response."""

    # Prices per 1 thousand tokens
    # https://mistral.ai/technology/
    model_cost_map = {
        "open-mistral-7b": {"input": 0.00025, "output": 0.00025},
        "open-mixtral-8x7b": {"input": 0.0007, "output": 0.0007},
        "open-mixtral-8x22b": {"input": 0.002, "output": 0.006},
        "mistral-small-latest": {"input": 0.001, "output": 0.003},
        "mistral-medium-latest": {"input": 0.00275, "output": 0.0081},
        "mistral-large-latest": {"input": 0.0003, "output": 0.0003},
        "mistral-large-2407": {"input": 0.0003, "output": 0.0003},
        "open-mistral-nemo-2407": {"input": 0.0003, "output": 0.0003},
        "codestral-2405": {"input": 0.001, "output": 0.003},
    }

    # Ensure we have the model they are using and return the total cost
    if model_name in model_cost_map:
        costs = model_cost_map[model_name]

        return (input_tokens * costs["input"] / 1000) + (output_tokens * costs["output"] / 1000)
    else:
        warnings.warn(f"Cost calculation is not implemented for model {model_name}, will return $0.", UserWarning)
        return 0
