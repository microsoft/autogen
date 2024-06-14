"""Create a OpenAI-compatible client using Mistral.AI's API.

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

        # Validate individual parameters
        def validate_parameter(
            param_name: str,
            allowed_types: Tuple,
            allow_None: bool,
            default_value: Any,
            numerical_bound: Tuple,
            allowed_values: list,
        ):
            param_value = params.get(param_name, default_value)
            warning = ""

            if not isinstance(param_value, allowed_types):
                if isinstance(allowed_types, tuple):
                    formatted_types = "(" + ", ".join(f"{t.__name__}" for t in allowed_types) + ")"
                else:
                    formatted_types = f"{allowed_types.__name__}"
                warning = f"must be of type {formatted_types}{'or None' if allow_None else ''}"
            elif param_value is None and not allow_None:
                warning = "cannot be None"
            elif numerical_bound:
                lower_bound, upper_bound = numerical_bound
                if (lower_bound is not None and param_value < lower_bound) or (
                    upper_bound is not None and param_value > upper_bound
                ):
                    warning = f"has numerical bounds, {'>= ' + lower_bound if lower_bound else ''}{' and ' if lower_bound and upper_bound else ''}{'<= ' + upper_bound if upper_bound else ''}{', or can be None' if allow_None else ''}"
            elif allowed_values:
                if not (allow_None and param_value is None):
                    if param_value not in allowed_values:
                        warning = (
                            f"must be one of these values [{allowed_values}]{', or can be None' if allow_None else ''}"
                        )

            # If we failed any checks, warn and set to default value
            if warning:
                warnings.warn(
                    f"Config error - {param_name} {warning}, defaulting to {default_value}.",
                    UserWarning,
                )
                param_value = default_value

            return param_value

        mistral_params = {}

        # Check that we have what we need to use Mistral.AI's API
        mistral_params["model"] = params.get("model", None)
        assert mistral_params[
            "model"
        ], "Please specify the 'model' in your config list entry to nominate the Mistral.ai model to use."

        # Validate allowed Mistral.AI parameters
        mistral_params["stream"] = validate_parameter("stream", bool, False, False, None, [False])
        mistral_params["temperature"] = validate_parameter("temperature", (int, float), True, 0.7, None, None)
        mistral_params["top_p"] = validate_parameter("top_p", (int, float), True, None, None, None)
        mistral_params["max_tokens"] = validate_parameter("max_tokens", int, True, None, (0, None), None)
        mistral_params["safe_prompt"] = validate_parameter("safe_prompt", bool, False, False, None, [True, False])
        mistral_params["random_seed"] = validate_parameter("random_seed", int, True, None, False, False)

        return mistral_params

    def create(self, params: Dict[str, Any]) -> ChatCompletion:
        """Create a completion for a given config.

        Args:
            params: The params for the completion.

        Returns:
            The completion.
        """
        if "tools" in params:
            converted_functions = params["tools"]
        else:
            converted_functions = None

        raw_contents = params["messages"]

        # Parse parameters to Mistral.AI API's parameters
        mistral_params = self.parse_params(params)

        mistral_messages = []
        for message in raw_contents:

            # Mistral
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

            elif message["role"] in ("system", "user", "assistant", "tool"):
                # Note this ChatMessage can take a 'name' but it is rejected by the Mistral API, so, no, the 'name' field is not used.
                mistral_messages.append(ChatMessage(role=message["role"], content=message["content"]))

            else:
                warnings.warn(f"Unknown message role {message['role']}", UserWarning)

        client = MistralClient(api_key=self.api_key)

        # If a 'system' message follows an 'assistant' message, change it to 'user'
        # This can occur when using LLM summarisation
        for i in range(1, len(mistral_messages)):
            if mistral_messages[i - 1].role == "assistant" and mistral_messages[i].role == "system":
                mistral_messages[i].role = "user"

        # TODO: Handle streaming

        try:
            mistral_response = client.chat(
                model=mistral_params["model"],
                messages=mistral_messages,
                tools=converted_functions,
                tool_choice="auto",
                temperature=mistral_params["temperature"],
                top_p=mistral_params["top_p"],
                max_tokens=mistral_params["max_tokens"],
                safe_prompt=mistral_params["safe_prompt"],
                random_seed=mistral_params["random_seed"],
            )
        except MistralAPIException as e:
            raise RuntimeError(f"Mistral.AI exception occurred while calling Mistral.AI API: {e}")

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

        # Convert Mistral response to OAI compatible format for AutoGen
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
            created=int(time.time() * 1000),
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
