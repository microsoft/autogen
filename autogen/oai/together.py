"""Create an OpenAI-compatible client using Together.AI's API.

Example:
    llm_config={
        "config_list": [{
            "api_type": "together",
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "api_key": os.environ.get("TOGETHER_API_KEY")
            }
    ]}

    agent = autogen.AssistantAgent("my_agent", llm_config=llm_config)

Install Together.AI python library using: pip install --upgrade together

Resources:
- https://docs.together.ai/docs/inference-python
"""

from __future__ import annotations

import base64
import copy
import os
import random
import re
import time
import warnings
from io import BytesIO
from typing import Any, Dict, List, Mapping, Tuple, Union

import requests
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage
from PIL import Image
from together import Together, error

from autogen.oai.client_utils import should_hide_tools, validate_parameter


class TogetherClient:
    """Client for Together.AI's API."""

    def __init__(self, **kwargs):
        """Requires api_key or environment variable to be set

        Args:
            api_key (str): The API key for using Together.AI (or environment variable TOGETHER_API_KEY needs to be set)
        """
        # Ensure we have the api_key upon instantiation
        self.api_key = kwargs.get("api_key", None)
        if not self.api_key:
            self.api_key = os.getenv("TOGETHER_API_KEY")

        assert (
            self.api_key
        ), "Please include the api_key in your config list entry for Together.AI or set the TOGETHER_API_KEY env variable."

    def message_retrieval(self, response) -> List:
        """
        Retrieve and return a list of strings or a list of Choice.Message from the response.

        NOTE: if a list of Choice.Message is returned, it currently needs to contain the fields of OpenAI's ChatCompletion Message object,
        since that is expected for function or tool calling in the rest of the codebase at the moment, unless a custom agent is being used.
        """
        return [choice.message for choice in response.choices]

    def cost(self, response) -> float:
        return response.cost

    @staticmethod
    def get_usage(response) -> Dict:
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
        """Loads the parameters for Together.AI API from the passed in parameters and returns a validated set. Checks types, ranges, and sets defaults"""
        together_params = {}

        # Check that we have what we need to use Together.AI's API
        together_params["model"] = params.get("model", None)
        assert together_params[
            "model"
        ], "Please specify the 'model' in your config list entry to nominate the Together.AI model to use."

        # Validate allowed Together.AI parameters
        # https://github.com/togethercomputer/together-python/blob/94ffb30daf0ac3e078be986af7228f85f79bde99/src/together/resources/completions.py#L44
        together_params["max_tokens"] = validate_parameter(params, "max_tokens", int, True, 512, (0, None), None)
        together_params["stream"] = validate_parameter(params, "stream", bool, False, False, None, None)
        together_params["temperature"] = validate_parameter(params, "temperature", (int, float), True, None, None, None)
        together_params["top_p"] = validate_parameter(params, "top_p", (int, float), True, None, None, None)
        together_params["top_k"] = validate_parameter(params, "top_k", int, True, None, None, None)
        together_params["repetition_penalty"] = validate_parameter(
            params, "repetition_penalty", float, True, None, None, None
        )
        together_params["presence_penalty"] = validate_parameter(
            params, "presence_penalty", (int, float), True, None, (-2, 2), None
        )
        together_params["frequency_penalty"] = validate_parameter(
            params, "frequency_penalty", (int, float), True, None, (-2, 2), None
        )
        together_params["min_p"] = validate_parameter(params, "min_p", (int, float), True, None, (0, 1), None)
        together_params["safety_model"] = validate_parameter(
            params, "safety_model", str, True, None, None, None
        )  # We won't enforce the available models as they are likely to change

        # Check if they want to stream and use tools, which isn't currently supported (TODO)
        if together_params["stream"] and "tools" in params:
            warnings.warn(
                "Streaming is not supported when using tools, streaming will be disabled.",
                UserWarning,
            )

            together_params["stream"] = False

        return together_params

    def create(self, params: Dict) -> ChatCompletion:

        messages = params.get("messages", [])

        # Convert AutoGen messages to Together.AI messages
        together_messages = oai_messages_to_together_messages(messages)

        # Parse parameters to Together.AI API's parameters
        together_params = self.parse_params(params)

        # Add tools to the call if we have them and aren't hiding them
        if "tools" in params:
            hide_tools = validate_parameter(
                params, "hide_tools", str, False, "never", None, ["if_all_run", "if_any_run", "never"]
            )
            if not should_hide_tools(together_messages, params["tools"], hide_tools):
                together_params["tools"] = params["tools"]

        together_params["messages"] = together_messages

        # We use chat model by default
        client = Together(api_key=self.api_key)

        # Token counts will be returned
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        max_retries = 5
        for attempt in range(max_retries):
            ans = None
            try:
                response = client.chat.completions.create(**together_params)
            except Exception as e:
                raise RuntimeError(f"Together.AI exception occurred: {e}")
            else:

                if together_params["stream"]:
                    # Read in the chunks as they stream
                    ans = ""
                    for chunk in response:
                        ans = ans + (chunk.choices[0].delta.content or "")

                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens
                    total_tokens = chunk.usage.total_tokens
                else:
                    ans: str = response.choices[0].message.content

                    prompt_tokens = response.usage.prompt_tokens
                    completion_tokens = response.usage.completion_tokens
                    total_tokens = response.usage.total_tokens
                break

        if response is not None:
            # If we have tool calls as the response, populate completed tool calls for our return OAI response
            if response.choices[0].finish_reason == "tool_calls":
                together_finish = "tool_calls"
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
                together_finish = "stop"
                tool_calls = None

        else:
            raise RuntimeError(f"Failed to get response from Together.AI after retrying {attempt + 1} times.")

        # 3. convert output
        message = ChatCompletionMessage(
            role="assistant",
            content=response.choices[0].message.content,
            function_call=None,
            tool_calls=tool_calls,
        )
        choices = [Choice(finish_reason=together_finish, index=0, message=message)]

        response_oai = ChatCompletion(
            id=response.id,
            model=together_params["model"],
            created=int(time.time()),
            object="chat.completion",
            choices=choices,
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            cost=calculate_together_cost(prompt_tokens, completion_tokens, together_params["model"]),
        )

        return response_oai


def oai_messages_to_together_messages(messages: list[Dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert messages from OAI format to Together.AI format.
    We correct for any specific role orders and types.
    """

    together_messages = copy.deepcopy(messages)

    # If we have a message with role='tool', which occurs when a function is executed, change it to 'user'
    for msg in together_messages:
        if "role" in msg and msg["role"] == "tool":
            msg["role"] = "user"

    return together_messages


# MODELS AND COSTS
chat_lang_code_model_sizes = {
    "zero-one-ai/Yi-34B-Chat": 34,
    "allenai/OLMo-7B-Instruct": 7,
    "allenai/OLMo-7B-Twin-2T": 7,
    "allenai/OLMo-7B": 7,
    "Austism/chronos-hermes-13b": 13,
    "deepseek-ai/deepseek-coder-33b-instruct": 33,
    "deepseek-ai/deepseek-llm-67b-chat": 67,
    "garage-bAInd/Platypus2-70B-instruct": 70,
    "google/gemma-2b-it": 2,
    "google/gemma-7b-it": 7,
    "Gryphe/MythoMax-L2-13b": 13,
    "lmsys/vicuna-13b-v1.5": 13,
    "lmsys/vicuna-7b-v1.5": 7,
    "codellama/CodeLlama-13b-Instruct-hf": 13,
    "codellama/CodeLlama-34b-Instruct-hf": 34,
    "codellama/CodeLlama-70b-Instruct-hf": 70,
    "codellama/CodeLlama-7b-Instruct-hf": 7,
    "meta-llama/Llama-2-70b-chat-hf": 70,
    "meta-llama/Llama-2-13b-chat-hf": 13,
    "meta-llama/Llama-2-7b-chat-hf": 7,
    "meta-llama/Llama-3-8b-chat-hf": 8,
    "meta-llama/Llama-3-70b-chat-hf": 70,
    "mistralai/Mistral-7B-Instruct-v0.1": 7,
    "mistralai/Mistral-7B-Instruct-v0.2": 7,
    "mistralai/Mistral-7B-Instruct-v0.3": 7,
    "NousResearch/Nous-Capybara-7B-V1p9": 7,
    "NousResearch/Nous-Hermes-llama-2-7b": 7,
    "NousResearch/Nous-Hermes-Llama2-13b": 13,
    "NousResearch/Nous-Hermes-2-Yi-34B": 34,
    "openchat/openchat-3.5-1210": 7,
    "Open-Orca/Mistral-7B-OpenOrca": 7,
    "Qwen/Qwen1.5-0.5B-Chat": 0.5,
    "Qwen/Qwen1.5-1.8B-Chat": 1.8,
    "Qwen/Qwen1.5-4B-Chat": 4,
    "Qwen/Qwen1.5-7B-Chat": 7,
    "Qwen/Qwen1.5-14B-Chat": 14,
    "Qwen/Qwen1.5-32B-Chat": 32,
    "Qwen/Qwen1.5-72B-Chat": 72,
    "Qwen/Qwen1.5-110B-Chat": 110,
    "Qwen/Qwen2-72B-Instruct": 72,
    "snorkelai/Snorkel-Mistral-PairRM-DPO": 7,
    "togethercomputer/alpaca-7b": 7,
    "teknium/OpenHermes-2-Mistral-7B": 7,
    "teknium/OpenHermes-2p5-Mistral-7B": 7,
    "togethercomputer/Llama-2-7B-32K-Instruct": 7,
    "togethercomputer/RedPajama-INCITE-Chat-3B-v1": 3,
    "togethercomputer/RedPajama-INCITE-7B-Chat": 7,
    "togethercomputer/StripedHyena-Nous-7B": 7,
    "Undi95/ReMM-SLERP-L2-13B": 13,
    "Undi95/Toppy-M-7B": 7,
    "WizardLM/WizardLM-13B-V1.2": 13,
    "upstage/SOLAR-10.7B-Instruct-v1.0": 11,
}

# Cost per million tokens based on up to X Billion parameters, e.g. up 4B is $0.1/million
chat_lang_code_model_costs = {4: 0.1, 8: 0.2, 21: 0.3, 41: 0.8, 80: 0.9, 110: 1.8}

mixture_model_sizes = {
    "cognitivecomputations/dolphin-2.5-mixtral-8x7b": 56,
    "databricks/dbrx-instruct": 132,
    "mistralai/Mixtral-8x7B-Instruct-v0.1": 47,
    "mistralai/Mixtral-8x22B-Instruct-v0.1": 141,
    "NousResearch/Nous-Hermes-2-Mistral-7B-DPO": 7,
    "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO": 47,
    "NousResearch/Nous-Hermes-2-Mixtral-8x7B-SFT": 47,
    "Snowflake/snowflake-arctic-instruct": 480,
}

# Cost per million tokens based on up to X Billion parameters, e.g. up 56B is $0.6/million
mixture_costs = {56: 0.6, 176: 1.2, 480: 2.4}


def calculate_together_cost(input_tokens: int, output_tokens: int, model_name: str) -> float:
    """Cost calculation for inference"""

    if model_name in chat_lang_code_model_sizes or model_name in mixture_model_sizes:
        cost_per_mil = 0

        # Chat, Language, Code models
        if model_name in chat_lang_code_model_sizes:
            size_in_b = chat_lang_code_model_sizes[model_name]

            for top_size in chat_lang_code_model_costs.keys():
                if size_in_b <= top_size:
                    cost_per_mil = chat_lang_code_model_costs[top_size]
                    break

        else:
            # Mixture-of-experts
            size_in_b = mixture_model_sizes[model_name]

            for top_size in mixture_costs.keys():
                if size_in_b <= top_size:
                    cost_per_mil = mixture_costs[top_size]
                    break

        if cost_per_mil == 0:
            warnings.warn("Model size doesn't align with cost structure.", UserWarning)

        return cost_per_mil * ((input_tokens + output_tokens) / 1e6)

    else:
        # Model is not in our list of models, can't determine the cost
        warnings.warn(
            "The model isn't catered for costing, to apply costs you can use the 'price' key on your config_list.",
            UserWarning,
        )

        return 0
