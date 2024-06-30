"""Create an OpenAI-compatible client using Yi's API.

Example:
    llm_config={
        "config_list": [{
            "api_type": "yi",
            "model": "yi-large",
            "api_key": os.environ.get("YI_API_KEY")
            }
    ]}

    agent = autogen.AssistantAgent("my_agent", llm_config=llm_config)

Resources:
- https://platform.01.ai/docs#get-started
"""
from __future__ import annotations

import warnings
from typing import Any, Dict, List
from openai import OpenAI
from openai.types.chat import ChatCompletion
from autogen.oai.client_utils import validate_parameter

# Cost per thousand tokens - Input / Output (NOTE: Convert $/Million to $/K)
YI_PRICING_1K = {
    "yi-large": (0.003, 0.003),
}

class YiClient:
    """Client for 01.AI's Yi series LLM API."""

    def __init__(self, **kwargs):
        """Initialize the YiClient with the provided API key and base URL."""
        self._oai_client = OpenAI(
            api_key=kwargs.get("api_key", None),
            base_url=kwargs.get("base_url", None),
        )

    def message_retrieval(self, response) -> List:
        """
        Retrieve and return a list of strings or a list of Choice.Message from the response.

        NOTE: if a list of Choice.Message is returned, it currently needs to contain the fields of OpenAI's ChatCompletion Message object,
        since that is expected for function or tool calling in the rest of the codebase at the moment, unless a custom agent is being used.
        """

        return [choice.message for choice in response.choices]

    def parse_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Loads the parameters for Yi API from the passed in parameters and returns a validated set. Checks types, ranges, and sets defaults"""
        yi_params = {}

        # Check that we have what we need to use Yi's API
        # We won't enforce the available models as they are likely to change
        yi_params["model"] = params.get("model", None)
        assert yi_params[
            "model"
        ], "Please specify the 'model' in your config list entry to nominate the Yi model to use."
        yi_params["messages"] = validate_parameter(params, "messages", list, True, [], None, None)

        # Validate allowed Yi parameters
        # https://platform.01.ai/docs#request-body
        yi_params["max_tokens"] = validate_parameter(params, "max_tokens", int, True, None, (0, None), None)
        yi_params["stream"] = validate_parameter(params, "stream", bool, True, False, None, None)
        yi_params["temperature"] = validate_parameter(params, "temperature", (int, float), True, 0.3, (0, 2), None)
        yi_params["top_p"] = validate_parameter(params, "top_p", (int, float), True, 0.9, (0, 1), None)

        # Yi parameters not supported by their models yet, ignoring
        # logit_bias, logprobs, top_logprobs

        # Yi parameters we are ignoring:
        # n (must be 1), response_format (to enforce JSON but needs prompting as well), user,
        # parallel_tool_calls (defaults to True), stop
        # function_call (deprecated), functions (deprecated)
        # tool_choice (none if no tools, auto if there are tools)

        return yi_params

    def create(self, params: Dict) -> ChatCompletion:
        """
        Yi API is highly compatible with OpenAI API, so we can use the OpenAI client to interact with Yi's API. The parameters are lightly validated before being passed to the OpenAI client.
        """
        yi_params = self.parse_params(params)

        response = self._oai_client.chat.completions.create(**yi_params)

        response.cost = calculate_yi_cost(response.usage.prompt_tokens, response.usage.completion_tokens, response.model)

        return response

    def cost(self, response) -> float:
        return response.cost

    @staticmethod
    def get_usage(response) -> Dict:
        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cost": response.cost,
            "model": response.model,
        }

def calculate_yi_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calculate the cost of the completion using the Yi pricing."""
    total = 0.0

    if model in YI_PRICING_1K:
        input_cost_per_k, output_cost_per_k = YI_PRICING_1K[model]
        input_cost = (input_tokens / 1000) * input_cost_per_k
        output_cost = (output_tokens / 1000) * output_cost_per_k
        total = input_cost + output_cost
    else:
        warnings.warn(f"Cost calculation not available for model {model}", UserWarning)

    return total
