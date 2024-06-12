"""Create a OpenAI-compatible client using Together. AI's API.

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
from typing import Any, Dict, List, Mapping, Union

import requests
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage
from PIL import Image

# pip install together
from together import Together, error


class TogetherClient:
    """Client for Together.AI's API."""

    def load_params(self, **kwargs):
        """Loads the parameters for Together.AI API from the config. We load them specifically here for loading, type checks and defaults"""

        self._config_model = kwargs.get("model", None)
        self._config_api_key = kwargs.get("api_key", None)

        self._config_max_tokens = kwargs.get("max_tokens", None)
        if self._config_max_tokens is not None and not isinstance(self._config_max_tokens, int):
            warnings.warn("Config error - max_tokens must be an int value or None, defaulting to 512", UserWarning)
            self._config_max_tokens = 512

        self._config_stream = kwargs.get("stream", False)
        if self._config_stream is not None and not isinstance(self._config_stream, bool):
            warnings.warn(
                "Config error - stream must be a bool value or None, defaulting to False. Note: Streaming is not yet handled.",
                UserWarning,
            )
            self._config_stream = False

        self._config_temperature = kwargs.get("temperature", None)
        if self._config_temperature is not None and not isinstance(self._config_temperature, float):
            warnings.warn("Config error - Temperature must be a float value or None, defaulting to None", UserWarning)
            self._config_temperature = None

        self._config_top_p = kwargs.get("top_p", None)
        if self._config_top_p is not None and not isinstance(self._config_top_p, float):
            warnings.warn("Config error - top_p must be a float value or None, defaulting to None", UserWarning)
            self._config_top_p = None

        self._config_top_k = kwargs.get("top_k", None)
        if self._config_top_k is not None and not isinstance(self._config_top_k, int):
            warnings.warn("Config error - top_k must be an int value or None, defaulting to None", UserWarning)
            self._config_top_k = None

        self._config_repetition_penalty = kwargs.get("repetition_penalty", None)
        if self._config_repetition_penalty is not None and not isinstance(self._config_repetition_penalty, float):
            warnings.warn(
                "Config error - repetition_penalty must be a float value or None, defaulting to None", UserWarning
            )
            self._config_repetition_penalty = None
        elif isinstance(self._config_repetition_penalty, float) and (
            self._config_repetition_penalty < -2 or self._config_repetition_penalty > 2
        ):
            warnings.warn("Config error - repetition_penalty must be between -2 and 2, defaulting to None", UserWarning)
            self._config_repetition_penalty = None

        self._config_presence_penalty = kwargs.get("presence_penalty", None)
        if self._config_presence_penalty is not None and not isinstance(self._config_presence_penalty, float):
            warnings.warn(
                "Config error - presence_penalty must be a float value or None, defaulting to None", UserWarning
            )
            self._config_presence_penalty = None

        self._config_frequency_penalty = kwargs.get("frequency_penalty", None)
        if self._config_frequency_penalty is not None and not isinstance(self._config_frequency_penalty, float):
            warnings.warn(
                "Config error - frequency_penalty must be a float value or None, defaulting to None", UserWarning
            )
            self._config_frequency_penalty = None
        elif isinstance(self._config_frequency_penalty, float) and (
            self._config_frequency_penalty < -2 or self._config_frequency_penalty > 2
        ):
            warnings.warn("Config error - frequency_penalty must be between -2 and 2, defaulting to None", UserWarning)
            self._config_frequency_penalty = None

        self._config_min_p = kwargs.get("min_p", None)
        if self._config_min_p is not None and not isinstance(self._config_min_p, float):
            warnings.warn("Config error - min_p must be a float value or None, defaulting to None", UserWarning)
            self._config_min_p = None
        elif isinstance(self._config_min_p, float) and (self._config_min_p < 0 or self._config_min_p > 1):
            warnings.warn("Config error - min_p must be between 0 and 1, defaulting to None", UserWarning)
            self._config_min_p = None

        self._config_safety_model = kwargs.get("safety_model", None)
        if self._config_safety_model is not None and not isinstance(self._config_safety_model, str):
            warnings.warn("Config error - safety_model must be a string value or None, defaulting to None", UserWarning)
            self._config_safety_model = None

    def __init__(self, **kwargs):

        # Load config from parameters, setting defaults, checking types
        self.load_params(**kwargs)

        # Check that we have what we need to use Mistral.AI's API
        assert (
            self._config_model
        ), "Please specify the 'model' in your config list entry to nominate the Together.AI model to use."

        if not self._config_api_key:
            self._config_api_key = os.getenv("TOGETHER_API_KEY")

        assert (
            self._config_api_key
        ), "Please provide api_key in your config list entry for Together.AI or set the TOGETHER_API_KEY env variable."

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

    def create(self, params: Dict) -> ChatCompletion:

        messages = params.get("messages", [])

        # Convert AutoGen messages to Together.AI messages
        together_messages = oai_messages_to_together_messages(messages)

        if self._config_stream and "tools" in params:

            # Streaming with tool calling is not supported (TODO)
            warnings.warn(
                "Streaming is not supported when using tools, streaming will be disabled.",
                UserWarning,
            )

            self._config_stream = False

        # We use chat model by default
        client = Together(api_key=self._config_api_key)

        # Token counts will be returned
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        max_retries = 5
        for attempt in range(max_retries):
            ans = None
            try:
                response = client.chat.completions.create(
                    model=self._config_model,
                    max_tokens=self._config_max_tokens,
                    temperature=self._config_temperature,
                    top_p=self._config_top_p,
                    top_k=self._config_top_k,
                    repetition_penalty=self._config_repetition_penalty,
                    presence_penalty=self._config_presence_penalty,
                    frequency_penalty=self._config_frequency_penalty,
                    min_p=self._config_min_p,
                    stream=self._config_stream,
                    messages=together_messages,  # Main messages
                    tool_choice=(
                        "auto" if "tools" in params else None
                    ),  # "auto",  # Model to select the tool/function, we could also set it to choose a specific one
                    tools=params.get("tools", None),  # Include any tools/functions
                    n=1,  # API supports more than one response, limiting to one
                    safety_model=self._config_safety_model,
                )
            except error.AuthenticationError as e:
                raise RuntimeError(
                    f"Together.AI AuthenticationError, ensure you have your Together.AI API key set: {e}"
                )
            except error.RateLimitError as e:
                raise RuntimeError(f"Together.AI RateLimitError, too many requests sent in a short period of time: {e}")
            except error.InvalidRequestError as e:
                raise RuntimeError(f"Together.AI InvalidRequestError: {e}")
            except Exception as e:
                raise RuntimeError(f"Together.AI exception occurred while calling Together.API: {e}")
            else:

                if self._config_stream:
                    # Read in the chunks as they stream
                    ans = ""
                    for chunk in response:
                        ans = ans + (chunk.choices[0].delta.content or "")

                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens
                    total_tokens = chunk.usage.total_tokens
                else:
                    ans: str = response.choices[0].message.content
                    # `ans = response.text` is unstable. Use the following code instead.

                    """
                    choice.message  # type: ignore [union-attr]
                    if choice.message.function_call is not None or choice.message.tool_calls is not None  # type: ignore [union-attr]
                    else choice.message.content
                    """

                    # Is it returning a function call
                    # toolcall_result = response.choices[0].messages.tool_calls[0]

                    prompt_tokens = response.usage.prompt_tokens
                    completion_tokens = response.usage.completion_tokens
                    total_tokens = response.usage.total_tokens

                    response.cost = 0  # MS Address later.

                    return response
                break

        if ans is None:
            raise RuntimeError(f"Fail to get response from Together.AI after retrying {attempt + 1} times.")

        # 3. convert output
        message = ChatCompletionMessage(role="assistant", content=ans, function_call=None, tool_calls=None)
        choices = [Choice(finish_reason="stop", index=0, message=message)]

        response_oai = ChatCompletion(
            id=str(random.randint(0, 1000)),
            model=self._config_model,
            created=int(time.time() * 1000),
            object="chat.completion",
            choices=choices,
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            cost=calculate_together_cost(prompt_tokens, completion_tokens, self._config_model),
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
        return 0
