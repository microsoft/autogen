"""Create an OpenAI-compatible client using Cohere's API.

Example:
    llm_config={
        "config_list": [{
            "api_type": "cohere",
            "model": "command-r-plus",
            "api_key": os.environ.get("COHERE_API_KEY")
            "client_name": "autogen-cohere", # Optional parameter
            }
    ]}

    agent = autogen.AssistantAgent("my_agent", llm_config=llm_config)

Install Cohere's python library using: pip install --upgrade cohere

Resources:
- https://docs.cohere.com/reference/chat
"""

from __future__ import annotations

import json
import logging
import os
import random
import sys
import time
import warnings
from typing import Any, Dict, List

from cohere import Client as Cohere
from cohere.types import ToolParameterDefinitionsValue, ToolResult
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage

from .client_utils import logger_formatter, validate_parameter

logger = logging.getLogger(__name__)
if not logger.handlers:
    # Add the console handler.
    _ch = logging.StreamHandler(stream=sys.stdout)
    _ch.setFormatter(logger_formatter)
    logger.addHandler(_ch)


COHERE_PRICING_1K = {
    "command-r-plus": (0.003, 0.015),
    "command-r": (0.0005, 0.0015),
    "command-nightly": (0.00025, 0.00125),
    "command": (0.015, 0.075),
    "command-light": (0.008, 0.024),
    "command-light-nightly": (0.008, 0.024),
}


class CohereClient:
    """Client for Cohere's API."""

    def __init__(self, **kwargs):
        """Requires api_key or environment variable to be set

        Args:
            api_key (str): The API key for using Cohere (or environment variable COHERE_API_KEY needs to be set)
        """
        # Ensure we have the api_key upon instantiation
        self.api_key = kwargs.get("api_key", None)
        if not self.api_key:
            self.api_key = os.getenv("COHERE_API_KEY")

        assert (
            self.api_key
        ), "Please include the api_key in your config list entry for Cohere or set the COHERE_API_KEY env variable."

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
        """Loads the parameters for Cohere API from the passed in parameters and returns a validated set. Checks types, ranges, and sets defaults"""
        cohere_params = {}

        # Check that we have what we need to use Cohere's API
        # We won't enforce the available models as they are likely to change
        cohere_params["model"] = params.get("model", None)
        assert cohere_params[
            "model"
        ], "Please specify the 'model' in your config list entry to nominate the Cohere model to use."

        # Validate allowed Cohere parameters
        # https://docs.cohere.com/reference/chat
        cohere_params["temperature"] = validate_parameter(
            params, "temperature", (int, float), False, 0.3, (0, None), None
        )
        cohere_params["max_tokens"] = validate_parameter(params, "max_tokens", int, True, None, (0, None), None)
        cohere_params["k"] = validate_parameter(params, "k", int, False, 0, (0, 500), None)
        cohere_params["p"] = validate_parameter(params, "p", (int, float), False, 0.75, (0.01, 0.99), None)
        cohere_params["seed"] = validate_parameter(params, "seed", int, True, None, None, None)
        cohere_params["frequency_penalty"] = validate_parameter(
            params, "frequency_penalty", (int, float), True, 0, (0, 1), None
        )
        cohere_params["presence_penalty"] = validate_parameter(
            params, "presence_penalty", (int, float), True, 0, (0, 1), None
        )

        # Cohere parameters we are ignoring:
        # preamble - we will put the system prompt in here.
        # parallel_tool_calls (defaults to True), perfect as is.
        # conversation_id - allows resuming a previous conversation, we don't support this.
        logging.info("Conversation ID: %s", params.get("conversation_id", "None"))
        # connectors - allows web search or other custom connectors, not implementing for now but could be useful in the future.
        logging.info("Connectors: %s", params.get("connectors", "None"))
        # search_queries_only - to control whether only search queries are used, we're not using connectors so ignoring.
        # documents - a list of documents that can be used to support the chat. Perhaps useful in the future for RAG.
        # citation_quality - used for RAG flows and dependent on other parameters we're ignoring.
        # max_input_tokens - limits input tokens, not needed.
        logging.info("Max Input Tokens: %s", params.get("max_input_tokens", "None"))
        # stop_sequences - used to stop generation, not needed.
        logging.info("Stop Sequences: %s", params.get("stop_sequences", "None"))

        return cohere_params

    def create(self, params: Dict) -> ChatCompletion:

        messages = params.get("messages", [])
        client_name = params.get("client_name") or "autogen-cohere"
        # Parse parameters to the Cohere API's parameters
        cohere_params = self.parse_params(params)
        # Convert AutoGen messages to Cohere messages
        cohere_messages, preamble, final_message = oai_messages_to_cohere_messages(messages, params, cohere_params)

        cohere_params["chat_history"] = cohere_messages
        cohere_params["message"] = final_message
        cohere_params["preamble"] = preamble

        # We use chat model by default
        client = Cohere(api_key=self.api_key, client_name=client_name)

        # Token counts will be returned
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        # Stream if in parameters
        streaming = True if "stream" in params and params["stream"] else False
        cohere_finish = ""

        max_retries = 5

        for attempt in range(max_retries):
            ans = None
            try:
                if streaming:
                    response = client.chat_stream(**cohere_params)
                else:
                    response = client.chat(**cohere_params)

            except CohereRateLimitError as e:
                raise RuntimeError(f"Cohere exception occurred: {e}")
            else:

                if streaming:
                    # Streaming...
                    ans = ""
                    for event in response:
                        if event.event_type == "text-generation":
                            ans = ans + event.text
                        elif event.event_type == "tool-calls-generation":
                            # When streaming, tool calls are compiled at the end into a single event_type
                            ans = event.text
                            cohere_finish = "tool_calls"
                            tool_calls = []
                            for tool_call in event.tool_calls:
                                tool_calls.append(
                                    ChatCompletionMessageToolCall(
                                        id=str(random.randint(0, 100000)),
                                        function={
                                            "name": tool_call.name,
                                            "arguments": (
                                                "" if tool_call.parameters is None else json.dumps(tool_call.parameters)
                                            ),
                                        },
                                        type="function",
                                    )
                                )

                    # Not using billed_units, but that may be better for cost purposes
                    prompt_tokens = event.response.meta.tokens.input_tokens
                    completion_tokens = event.response.meta.tokens.output_tokens
                    total_tokens = prompt_tokens + completion_tokens

                    response_id = event.response.response_id
                else:
                    # Non-streaming finished
                    ans: str = response.text

                    # Not using billed_units, but that may be better for cost purposes
                    prompt_tokens = response.meta.tokens.input_tokens
                    completion_tokens = response.meta.tokens.output_tokens
                    total_tokens = prompt_tokens + completion_tokens

                    response_id = response.response_id
                break

        if response is not None:

            response_content = ans

            if streaming:
                # Streaming response
                if cohere_finish == "":
                    cohere_finish = "stop"
                    tool_calls = None
            else:
                # Non-streaming response
                # If we have tool calls as the response, populate completed tool calls for our return OAI response
                if response.tool_calls is not None:
                    cohere_finish = "tool_calls"
                    tool_calls = []
                    for tool_call in response.tool_calls:

                        # if parameters are null, clear them out (Cohere can return a string "null" if no parameter values)

                        tool_calls.append(
                            ChatCompletionMessageToolCall(
                                id=str(random.randint(0, 100000)),
                                function={
                                    "name": tool_call.name,
                                    "arguments": (
                                        "" if tool_call.parameters is None else json.dumps(tool_call.parameters)
                                    ),
                                },
                                type="function",
                            )
                        )
                else:
                    cohere_finish = "stop"
                    tool_calls = None
        else:
            raise RuntimeError(f"Failed to get response from Cohere after retrying {attempt + 1} times.")

        # 3. convert output
        message = ChatCompletionMessage(
            role="assistant",
            content=response_content,
            function_call=None,
            tool_calls=tool_calls,
        )
        choices = [Choice(finish_reason=cohere_finish, index=0, message=message)]

        response_oai = ChatCompletion(
            id=response_id,
            model=cohere_params["model"],
            created=int(time.time()),
            object="chat.completion",
            choices=choices,
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            cost=calculate_cohere_cost(prompt_tokens, completion_tokens, cohere_params["model"]),
        )

        return response_oai


def extract_to_cohere_tool_results(tool_call_id: str, content_output: str, all_tool_calls) -> List[Dict[str, Any]]:
    temp_tool_results = []

    for tool_call in all_tool_calls:
        if tool_call["id"] == tool_call_id:

            call = {
                "name": tool_call["function"]["name"],
                "parameters": json.loads(
                    tool_call["function"]["arguments"] if not tool_call["function"]["arguments"] == "" else "{}"
                ),
            }
            output = [{"value": content_output}]
            temp_tool_results.append(ToolResult(call=call, outputs=output))
    return temp_tool_results


def is_recent_tool_call(messages: list[Dict[str, Any]], tool_call_index: int):
    messages_length = len(messages)
    if tool_call_index == messages_length - 1:
        return True
    elif messages[tool_call_index + 1].get("role", "").lower() not in ("chatbot"):
        return True
    return False


def oai_messages_to_cohere_messages(
    messages: list[Dict[str, Any]], params: Dict[str, Any], cohere_params: Dict[str, Any]
) -> tuple[list[dict[str, Any]], str, str]:
    """Convert messages from OAI format to Cohere's format.
    We correct for any specific role orders and types.

    Parameters:
        messages: list[Dict[str, Any]]: AutoGen messages
        params: Dict[str, Any]:         AutoGen parameters dictionary
        cohere_params: Dict[str, Any]:  Cohere parameters dictionary

    Returns:
        List[Dict[str, Any]]:   Chat History messages
        str:                    Preamble (system message)
        str:                    Message (the final user message)
    """

    cohere_messages = []
    preamble = ""
    cohere_tool_names = set()
    # Tools
    if "tools" in params:
        cohere_tools = []
        for tool in params["tools"]:

            # build list of properties
            parameters = {}

            for key, value in tool["function"]["parameters"]["properties"].items():
                type_str = value["type"]
                required = True  # Defaults to False, we could consider leaving it as default.
                description = value["description"]

                # If we have an 'enum' key, add that to the description (as not allowed to pass in enum as a field)
                if "enum" in value:
                    # Access the enum list
                    enum_values = value["enum"]
                    enum_strings = [str(value) for value in enum_values]
                    enum_string = ", ".join(enum_strings)
                    description = description + ". Possible values are " + enum_string + "."

                parameters[key] = ToolParameterDefinitionsValue(
                    description=description, type=type_str, required=required
                )

            cohere_tool = {
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "parameter_definitions": parameters,
            }
            cohere_tool_names.add(tool["function"]["name"] or "")

            cohere_tools.append(cohere_tool)

        if len(cohere_tools) > 0:
            cohere_params["tools"] = cohere_tools

    tool_calls = []
    tool_results = []

    # Rules for cohere messages:
    # no 'name' field
    # 'system' messages go into the preamble parameter
    # user role = 'USER'
    # assistant role = 'CHATBOT'
    # 'content' field renamed to 'message'
    # tools go into tools parameter
    # tool_results go into tool_results parameter
    for index, message in enumerate(messages):

        if not message["content"]:
            continue

        if "role" in message and message["role"] == "system":
            # System message
            if preamble == "":
                preamble = message["content"]
            else:
                preamble = preamble + "\n" + message["content"]

        elif message.get("tool_calls"):
            # Suggested tool calls, build up the list before we put it into the tool_results
            message_tool_calls = []
            for tool_call in message["tool_calls"] or []:
                if (not tool_call.get("function", {}).get("name")) or tool_call.get("function", {}).get(
                    "name"
                ) not in cohere_tool_names:
                    new_message = {
                        "role": "CHATBOT",
                        "message": message.get("name") + ":" + message["content"] + str(message["tool_calls"]),
                    }
                    cohere_messages.append(new_message)
                    continue

                tool_calls.append(tool_call)
                message_tool_calls.append(
                    {
                        "name": tool_call.get("function", {}).get("name"),
                        "parameters": json.loads(tool_call.get("function", {}).get("arguments") or "null"),
                    }
                )

            if not message_tool_calls:
                continue

            # We also add the suggested tool call as a message
            new_message = {
                "role": "CHATBOT",
                "message": message.get("name") + ":" + message["content"],
                "tool_calls": message_tool_calls,
            }

            cohere_messages.append(new_message)
        elif "role" in message and message["role"] == "tool":
            if not (tool_call_id := message.get("tool_call_id")):
                continue

            content_output = message["content"]
            if tool_call_id not in [tool_call["id"] for tool_call in tool_calls]:

                new_message = {
                    "role": "CHATBOT",
                    "message": content_output,
                }
                cohere_messages.append(new_message)
                continue

            # Convert the tool call to a result
            tool_results_chat_turn = extract_to_cohere_tool_results(tool_call_id, content_output, tool_calls)
            if is_recent_tool_call(messages, index):
                # If the tool call is the last message or the next message is a user/tool message, this is a recent tool call.
                # So, we pass it into tool_results.
                tool_results.extend(tool_results_chat_turn)
                continue

            else:
                # If its not the current tool call, we pass it as a tool message in the chat history.
                new_message = {"role": "TOOL", "tool_results": tool_results_chat_turn}
                cohere_messages.append(new_message)

        elif "content" in message and isinstance(message["content"], str):
            # Standard text message
            new_message = {
                "role": "USER" if message["role"] == "user" else "CHATBOT",
                "message": message.get("name") + ":" + message.get("content"),
            }

            cohere_messages.append(new_message)

    # Append any Tool Results
    if len(tool_results) != 0:
        cohere_params["tool_results"] = tool_results

        # Enable multi-step tool use: https://docs.cohere.com/docs/multi-step-tool-use
        cohere_params["force_single_step"] = False

        # If we're adding tool_results, like we are, the last message can't be a USER message
        # So, we add a CHATBOT 'continue' message, if so.
        # Changed key from "content" to "message" (jaygdesai/autogen_Jay)
        if cohere_messages[-1]["role"].lower() == "user":
            cohere_messages.append({"role": "CHATBOT", "message": "Please go ahead and follow the instructions!"})

        # We return a blank message when we have tool results
        # TODO: Check what happens if tool_results aren't the latest message
        return cohere_messages, preamble, ""

    else:

        # We need to get the last message to assign to the message field for Cohere,
        # if the last message is a user message, use that, otherwise put in 'continue'.
        if cohere_messages[-1]["role"] == "USER":
            return cohere_messages[0:-1], preamble, cohere_messages[-1]["message"]
        else:
            return cohere_messages, preamble, "Please go ahead and follow the instructions!"


def calculate_cohere_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calculate the cost of the completion using the Cohere pricing."""
    total = 0.0

    if model in COHERE_PRICING_1K:
        input_cost_per_k, output_cost_per_k = COHERE_PRICING_1K[model]
        input_cost = (input_tokens / 1000) * input_cost_per_k
        output_cost = (output_tokens / 1000) * output_cost_per_k
        total = input_cost + output_cost
    else:
        warnings.warn(f"Cost calculation not available for {model} model", UserWarning)

    return total


class CohereError(Exception):
    """Base class for other Cohere exceptions"""

    pass


class CohereRateLimitError(CohereError):
    """Raised when rate limit is exceeded"""

    pass
