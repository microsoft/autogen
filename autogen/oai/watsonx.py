"""Create an OpenAI-compatible client using Watsonx's API.

Example:
    llm_config={
        "config_list": [{
            "api_type": "watsonx",
            "model": "ibm/granite-3-8b-instruct",
            "api_key": os.environ.get("WATSONX_API_KEY"),
            "space_id": os.environ.get("WATSONX_SPACE_ID"),
            }
    ]}

    agent = autogen.AssistantAgent("my_agent", llm_config=llm_config)

Install Watsonx's python library using: pip install --upgrade ibm_watsonx_ai

Resources:
- https://cloud.ibm.com/apidocs/watsonx-ai#text-chat
- https://ibm.github.io/watsonx-ai-python-sdk/fm_model_inference.html#ibm_watsonx_ai.foundation_models.inference.ModelInference.chat
"""

from __future__ import annotations

import copy
import logging
import os
import sys
import time
import warnings
from typing import Any, Dict, Iterable, List, Optional

from ibm_watsonx_ai.foundation_models.model import ModelInference
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.chat.chat_completion_message_tool_call import Function
from openai.types.completion_usage import CompletionUsage

from .client_utils import logger_formatter, validate_parameter

logger = logging.getLogger(__name__)
if not logger.handlers:
    # Add the console handler.
    _ch = logging.StreamHandler(stream=sys.stdout)
    _ch.setFormatter(logger_formatter)
    logger.addHandler(_ch)


# see full lists of models on https://www.ibm.com/products/watsonx-ai/foundation-models#generative
# here only the latest IBM granite models are listed
WATSONX_PRICING_1K = {
    "ibm/granite-3-8b-instruct": (0.0002, 0.0002),
}


def calculate_watsonx_cost(prompt_tokens, completion_tokens, model_id):
    total = 0.0

    if model_id in WATSONX_PRICING_1K:
        input_cost_per_k, output_cost_per_k = WATSONX_PRICING_1K[model_id]
        input_cost = (prompt_tokens / 1000) * input_cost_per_k
        output_cost = (completion_tokens / 1000) * output_cost_per_k
        total = input_cost + output_cost
    else:
        warnings.warn(f"Cost calculation not available for {model_id} model", UserWarning)

    return total


class WatsonxClient:
    """Client for Watsonx's API."""

    def __init__(self, **kwargs):
        """Requires api_key or environment variable to be set.
        Requires one of space_id or project_id
        URL is optional and defaults to US south Watsonx SaaS deployment

        Args:
            api_key (str): The API key for using Watsonx (or environment variable WATSONX_API_KEY needs to be set)
            url (str): The Watsonx instance url for using Watsonx (or environment variable WATSONX_URL can be set)
            space_id (str): The space id for using Watsonx (or environment variable WATSONX_SPACE_ID needs to be set)
            project_id (str): The project id for using Watsonx (or environment variable WATSONX_PROJECT_ID needs to be set)
        """
        # url
        self.url = kwargs.get("url", None)
        if not self.url:
            self.url = os.getenv("WATSONX_URL")
        if not self.url:
            self.url = "https://us-south.ml.cloud.ibm.com"

        # api key is required
        self.api_key = kwargs.get("api_key", None)
        if not self.api_key:
            self.api_key = os.getenv("WATSONX_API_KEY")
        assert (
            self.api_key
        ), "Please include the api_key in your config list entry for Watsonx or set the WATSONX_API_KEY env variable."

        # one of space_id or project_id should be provided
        self.space_id = kwargs.get("space_id", None)
        if not self.space_id:
            self.space_id = os.getenv("WATSONX_SPACE_ID")
        self.project_id = kwargs.get("project_id", None)
        if not self.project_id:
            self.project_id = os.getenv("WATSONX_PROJECT_ID")
        assert (
            self.space_id or self.project_id
        ), "Please include the space_id/project_id in your config list entry for Watsonx or set the WATSONX_SPACE_ID/WATSONX_PROJECT_ID env variable."

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
        """Loads the parameters for Watsonx API from the passed in parameters and returns a validated set. Checks types, ranges, and sets defaults"""
        wx_params = {}
        # Validate allowed Watsonx parameters
        # https://ibm.github.io/watsonx-ai-python-sdk/fm_schema.html#ibm_watsonx_ai.foundation_models.schema.TextChatParameters
        # https://cloud.ibm.com/apidocs/watsonx-ai#text-chat
        wx_params["frequency_penalty"] = validate_parameter(
            params, "frequency_penalty", (int, float), True, None, (0, 1), None
        )
        wx_params["max_tokens"] = validate_parameter(params, "max_tokens", (int,), True, None, (0, None), None)
        wx_params["presence_penalty"] = validate_parameter(
            params, "presence_penalty", (int, float), True, None, (0, 1), None
        )
        wx_params["temperature"] = validate_parameter(params, "temperature", (int, float), True, None, (0, None), None)
        wx_params["top_p"] = validate_parameter(params, "top_p", (int, float), True, None, (0.01, 0.99), None)

        # ignored params:
        # logprobs/top_logprobs: this is only for returning the logits
        # response_format: leave as default, which is json https://ibm.github.io/watsonx-ai-python-sdk/fm_schema.html#ibm_watsonx_ai.foundation_models.schema.TextChatResponseFormatType
        # time_limit
        # n: How many chat completion choices to generate for each input message.

        return wx_params

    def create(self, params: Dict) -> ChatCompletion:
        # get model id
        model_id = params.get("model", None)
        assert model_id, "Please specify `model` in the config list entry for which Watsonx model to use"
        # chat/chat_stream args
        _messages = params.get("messages", [])
        wx_params = self.parse_params(params)
        messages, tools, tool_choice, tool_choice_option = oai_messages_to_watsonx_messages(_messages, params)

        # We use chat model by default
        client = ModelInference(
            model_id=model_id,
            credentials={
                "api_key": self.api_key,
                "url": self.url,
            },
            space_id=self.space_id,
            project_id=self.project_id,
            params=wx_params,
        )

        # Stream if in parameters
        streaming = True if "stream" in params and params["stream"] else False

        # make the call to watsonx api
        if streaming:
            response = client.chat_stream(
                messages=messages,
                params=wx_params,
                tools=tools,
                tool_choice=tool_choice,
                tool_choice_option=tool_choice_option,
            )
        else:
            response = client.chat(
                messages=messages,
                params=wx_params,
                tools=tools,
                tool_choice=tool_choice,
                tool_choice_option=tool_choice_option,
            )

        # response parsing
        if streaming:
            # components for full final response
            response_id = ""
            response_content = ""
            finish_reason = ""
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            created = 0
            full_tool_calls: Optional[List[Optional[Dict[str, Any]]]] = None

            # Send the chat completion request to OpenAI's API and process the response in chunks
            for chunk in response:
                if chunk.get("choices", []):
                    choice = chunk["choices"][0]

                    # update metadata with the last chunk
                    if choice["finish_reason"]:
                        response_id = chunk["id"]
                        finish_reason = choice["finish_reason"]
                        prompt_tokens = choice["usage"]["prompt_tokens"]
                        completion_tokens = choice["usage"]["completion_tokens"]
                        total_tokens = choice["usage"]["total_tokens"]
                        created = chunk["created"]

                    # concatenate content
                    _content = choice["delta"].get("content")
                    if _content:
                        _content = _content_str_repr(_content)
                    if _content:
                        response_content += _content

                    # concatenate tool calls
                    tool_calls_chunks = choice["delta"].get("tool_calls", [])
                    if tool_calls_chunks:
                        for tool_calls_chunk in tool_calls_chunks:
                            # the current tool call to be reconstructed
                            ix = tool_calls_chunk["index"]
                            if full_tool_calls is None:
                                full_tool_calls = []
                            if ix >= len(full_tool_calls):
                                # in case ix is not sequential
                                full_tool_calls = full_tool_calls + [None] * (ix - len(full_tool_calls) + 1)
                            if full_tool_calls[ix] is None:
                                full_tool_calls[ix] = {}
                            full_tool_calls[ix]["name"] += tool_calls_chunk["function"]["name"]
                            full_tool_calls[ix]["arguments"] += tool_calls_chunk["function"]["arguments"]
                            if "id" not in full_tool_calls[ix] and "id" in tool_calls_chunk:
                                full_tool_calls[ix]["id"] = tool_calls_chunk["id"]

            message = ChatCompletionMessage(
                content=response_content,
                role="assistant",
                tool_calls=(
                    [
                        ChatCompletionMessageToolCall(
                            id=tool_call["id"],
                            function=Function(
                                name=tool_call["name"],
                                arguments=tool_call["arguments"],
                            ),
                            type="function",
                        )
                        for tool_call in full_tool_calls
                    ]
                    if full_tool_calls
                    else None
                ),
            )
            choice = Choice(finish_reason=finish_reason, index=0, message=message)
            response_oai = ChatCompletion(
                id=response_id,
                model=model_id,
                created=created,
                object="chat.completion",
                choices=[choice],
                usage=CompletionUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                ),
                cost=calculate_watsonx_cost(prompt_tokens, completion_tokens, model_id),
            )
        else:
            # Non-streaming finished
            choice = response["choices"][0]
            message = ChatCompletionMessage(
                content=_content_str_repr(choice["message"]["content"]) if "content" in choice["message"] else None,
                role="assistant",
                tool_calls=(
                    [
                        ChatCompletionMessageToolCall(
                            id=tool_call["id"],
                            function=Function(
                                name=tool_call["function"]["name"],
                                arguments=tool_call["function"]["arguments"],
                            ),
                            type="function",
                        )
                        for tool_call in choice["message"]["tool_calls"]
                    ]
                    if choice["message"].get("tool_calls")
                    else None
                ),
            )
            choices = [Choice(finish_reason=choice["finish_reason"], index=0, message=message)]
            prompt_tokens = response["usage"]["prompt_tokens"]
            completion_tokens = response["usage"]["completion_tokens"]
            total_tokens = response["usage"]["total_tokens"]
            response_id = response["id"]

            response_oai = ChatCompletion(
                id=response_id,
                model=model_id,
                created=int(time.time()),
                object="chat.completion",
                choices=choices,
                usage=CompletionUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                ),
                cost=calculate_watsonx_cost(prompt_tokens, completion_tokens, model_id),
            )
        return response_oai


def oai_messages_to_watsonx_messages(
    messages: list[Dict[str, Any]], params: Dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]] | None, dict[str, Any] | None, str | None]:
    """Convert messages from OAI format to Watsonx's format, which is mostly consistent with OAI format at the time of writing.
     https://cloud.ibm.com/apidocs/watsonx-ai#text-chat

    Parameters:
        messages: list[Dict[str, Any]]: AutoGen messages
        params: Dict[str, Any]:         AutoGen parameters dictionary

    Returns:
        List[Dict[str, Any]]:              Chat History messages
        list[dict[str, Any]] | None:       tools (list of available tools)
        dict[str, Any] | None:             Specifying a particular tool to force the model to call that tool.
        str | None:                        tool choice option
    """

    # Tools
    tools = params.get("tools", None)

    oai_tool_choice = params.get("tool_choice", None)
    tool_choice = None
    tool_choice_option = None
    if oai_tool_choice is not None:
        if isinstance(oai_tool_choice, str):
            tool_choice_option = oai_tool_choice
        else:
            tool_choice = oai_tool_choice

    # messages
    wx_messages = copy.deepcopy(messages)

    return wx_messages, tools, tool_choice, tool_choice_option


def _content_str_repr(content: str | list[dict[str, Any]]):
    """content in message can be a string or a list of dictionaries"""
    if isinstance(content, str):
        return content
    elif isinstance(content, Iterable) and len(content) > 0:
        return content[0].get("text")
    else:
        return None
