# Important notes when using the Mistral.AI API:
# The first system message can greatly affect whether the model returns a tool call, including text that references the ability to use functions will help.
# Changing the role on the first system message to 'user' improved the chances of the model recommending a tool call.

import inspect
import json
import os
import time
import warnings
from typing import Any, Dict, List, Union

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

    # Mapping, where Key is a term used by Autogen, and Value is a term used by Mistral.AI
    PARAMS_MAPPING = {
        "temperature": "temperature",
        "top_p": "top_p",
        "max_tokens": "max_tokens",
        "random_seed": "random_seed",
    }

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self.model = config.get("model", None)

        assert (
            self.model
        ), "Please specify the 'model' in your config list entry to nominate the Mistral.ai model to use."

        self.api_key = config.get("api_key", None)
        if not self.api_key:
            self.api_key = os.getenv("MISTRAL_API_KEY")

        assert (
            self.api_key
        ), "Please specify the 'api_key' in your config list entry for Mistral or set the MISTRAL_API_KEY env variable."

    def message_retrieval(self, response: ChatCompletionResponse) -> Union[List[str], List[ChatCompletionMessage]]:
        """Retrieve the messages from the response."""

        return [choice.message for choice in response.choices]

    def cost(self, response) -> float:
        return response.cost

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

        try:
            mistral_response = client.chat(
                model=self.model,
                messages=mistral_messages,
                tools=converted_functions,
                tool_choice="auto",
                temperature=self._config.get("temperature", 0.7),
                top_p=self._config.get("top_p", 1),
                max_tokens=self._config.get("max_tokens", None),
                safe_prompt=self._config.get("safe_prompt", False),
                random_seed=self._config.get("random_seed", None),
            )
        except MistralAPIException:
            raise RuntimeError("Mistral.AI exception occurred while calling Mistral.AI API")

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
