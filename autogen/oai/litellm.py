"""Create an OpenAI-compatible client using LiteLLM's API. Note: This is for use with Ollama, specifically.

Example:
    llm_config={
        "config_list": [{
            "api_type": "litellm",
            "model": "ollama_chat/mistral:7b-instruct-v0.3-q6_K"
            }
    ]}

    agent = autogen.AssistantAgent("my_agent", llm_config=llm_config)

Install LiteLLM's python library using: pip install --upgrade litellm

Resources:
- https://docs.litellm.ai/docs/#basic-usage
"""

from __future__ import annotations

import copy
import json
import os
import random
import time
import warnings
from typing import Any, Dict, List, Tuple

import litellm
from litellm import completion
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage

from autogen.oai.client_utils import should_hide_tools, validate_parameter


class LiteLLMClient:
    """Client for LiteLLM's API."""

    def __init__(self, **kwargs):
        """Note that no api_key or environment variable is required as we're using LiteLLM only for Ollama.

        Args:
            None
        """

        # If you need to see more information, set to True
        litellm.set_verbose = False

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
        """Loads the parameters for LiteLLM API from the passed in parameters and returns a validated set. Checks types, ranges, and sets defaults"""
        litellm_params = {}

        # Check that we have what we need to use LiteLLM's API
        # https://docs.litellm.ai/docs/completion/input
        # We won't enforce the available models
        litellm_params["model"] = params.get("model", None)
        assert litellm_params[
            "model"
        ], "Please specify the 'model' in your config list entry to nominate the LiteLLM model to use. The model must start with 'ollama/' or 'ollama_chat/'."

        assert litellm_params["model"].startswith("ollama") or litellm_params["model"].startswith(
            "ollama_chat"
        ), "The model must start with 'ollama/' or 'ollama_chat/'."

        litellm_params["api_base"] = params.get("api_base", None)
        assert litellm_params[
            "api_base"
        ], "Please specify the 'api_base' in your config list entry to indicate the path to your Ollama server, e.g. 'http://localhost:11434'."

        # Validate allowed Groq parameters
        # https://console.groq.com/docs/api-reference#chat
        litellm_params["max_tokens"] = validate_parameter(params, "max_tokens", int, True, None, (0, None), None)
        litellm_params["presence_penalty"] = validate_parameter(
            params, "presence_penalty", (int, float), True, None, (-2, 2), None
        )
        litellm_params["stream"] = validate_parameter(params, "stream", bool, True, False, None, None)
        litellm_params["temperature"] = validate_parameter(params, "temperature", (int, float), True, 1, (0, 2), None)
        litellm_params["top_p"] = validate_parameter(params, "top_p", (int, float), True, None, None, None)

        # We include token usage statistics for streaming if streaming enabled
        litellm_params["stream_options"] = {"include_usage": True if litellm_params["stream"] else False}

        # An Ollama-specific parameter called format is available to force a json response
        # See: https://docs.litellm.ai/docs/providers/ollama#example-usage---json-mode

        # LiteLLM has other parameters but they are not supported by the Ollama integration

        return litellm_params

    def create(self, params: Dict) -> ChatCompletion:

        messages = params.get("messages", [])

        # Convert AutoGen messages to LiteLLM messages
        litellm_messages = oai_messages_to_litellm_messages(messages)

        # Parse parameters to the Groq API's parameters
        litellm_params = self.parse_params(params)

        # Add tools to the call if we have them and aren't hiding them
        if "tools" in params:
            hide_tools = validate_parameter(
                params, "hide_tools", str, False, "never", None, ["if_all_run", "if_any_run", "never"]
            )
            if not should_hide_tools(litellm_messages, params["tools"], hide_tools):
                # litellm_params["tools"] = params["tools"]
                add_tools_to_prompt(litellm_messages, params["tools"])
                # Test adding the tools in to the prompt

        litellm_params["format"] = ""  # TEST not JSON

        litellm_params["messages"] = litellm_messages

        # Token counts will be returned
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        # Streaming tool call recommendations
        streaming_tool_calls = []

        ans = None
        try:
            response = completion(**litellm_params)
        except Exception as e:
            raise RuntimeError(f"LiteLLM exception occurred: {e}")
        else:

            # Output from LiteLLM: https://docs.litellm.ai/docs/completion/output

            if litellm_params["stream"]:
                # Read in the chunks as they stream, taking in tool_calls which may be across
                # multiple chunks if more than one suggested
                ans = ""
                for chunk in response:
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

                    if hasattr(chunk, "usage"):
                        prompt_tokens = chunk.usage.prompt_tokens
                        completion_tokens = chunk.usage.completion_tokens
                        total_tokens = chunk.usage.total_tokens
            else:
                # Non-streaming finished
                ans: str = response.choices[0].message.content

                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens

        if response is not None:

            if litellm_params["stream"]:
                # Streaming response
                if chunk.choices[0].finish_reason == "tool_calls":
                    litellm_finish = "tool_calls"
                    tool_calls = streaming_tool_calls
                else:
                    litellm_finish = "stop"
                    tool_calls = None

                response_content = ans
                response_id = chunk.id
            else:

                tool_call_json, is_tool_call = validate_tool_call_json(ans)
                if is_tool_call:
                    # JSON response we'll temporarily assume is a function call

                    litellm_finish = "tool_calls"
                    tool_calls = []

                    for json_function in tool_call_json:
                        tool_calls.append(
                            ChatCompletionMessageToolCall(
                                id="litellm_func_{}".format(random.randint(0, 10000)),
                                function={
                                    "name": json_function["name"],
                                    "arguments": json.dumps(json_function["arguments"]),
                                },
                                type="function",
                            )
                        )

                    # Blank the message content
                    response_content = ""
                else:
                    response_content = response.choices[0].message.content
                    litellm_finish = "stop"
                    tool_calls = None

                """
                # Non-streaming response
                # If we have tool calls as the response, populate completed tool calls for our return OAI response
                if response.choices[0].finish_reason == "tool_calls":
                    litellm_finish = "tool_calls"
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
                    litellm_finish = "stop"
                    tool_calls = None
                """

                response_id = response.id
        else:
            raise RuntimeError("Failed to get response from Groq after retrying 5 times.")

        # 3. convert output
        message = ChatCompletionMessage(
            role="assistant",
            content=response_content,
            function_call=None,
            tool_calls=tool_calls,
        )
        choices = [Choice(finish_reason=litellm_finish, index=0, message=message)]

        response_oai = ChatCompletion(
            id=response_id,
            model=litellm_params["model"],
            created=int(time.time()),
            object="chat.completion",
            choices=choices,
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            cost=0,  # Local models, FREE!
        )

        return response_oai


def oai_messages_to_litellm_messages(messages: list[Dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert messages from OAI format to LiteLLM's format.
    We correct for any specific role orders and types.
    """

    litellm_messages = copy.deepcopy(messages)

    # Remove the name field
    for message in litellm_messages:
        if "name" in message:
            message.pop("name", None)

    # IMPORTANT: LiteLLM's Ollama library changes 'tool' roles to 'assistant'

    # If the last message is the result of a tool call, add a user message indicating that
    if litellm_messages[-1]["role"] == "tool":
        litellm_messages.append(
            {
                "role": "user",
                "content": "Please note the result of that function/tool call and do not call that function/tool again.",
            }
        )

    # Ensure the last message is a user message, if not, add a user message
    if litellm_messages[-1]["role"] != "user":
        litellm_messages.append({"role": "user", "content": "Please continue."})

    return litellm_messages


def validate_tool_call_json(response_str) -> Tuple[list, bool]:
    """Is the response string a JSON tool call? Validates the format and returns the validated json if it is and whether it is."""
    json_ans, valid_json = is_valid_json(response_str)

    if valid_json:
        response_json = json.loads(json_ans)

        if not isinstance(response_json, list):  # Put it into a list if it's not already
            response_json = [response_json]

        invalid_functions = False

        for json_function in response_json:
            # Must have name and arguments
            if "name" in json_function and "arguments" in json_function:
                arguments = json_function["arguments"]
                # Arguments must be a dictionary
                if not isinstance(arguments, dict):
                    invalid_functions = True
            else:
                invalid_functions = True

        return response_json if not invalid_functions else [], not invalid_functions

    else:
        return [], False


# TEMP TEMP TEMP
def is_valid_json(json_str) -> Tuple[str, bool]:
    try:
        json.loads(json_str)
        return json_str, True
    except json.JSONDecodeError:
        return fix_json_string(json_str)


def fix_json_string(json_string) -> Tuple[str, bool]:
    """Corrects a malformed JSON string by wrapping objects in an array."""
    lines = json_string.splitlines()
    if len(lines) > 1:
        # If there are multiple objects, wrap them in an array
        fixed_string = f"[{''.join(lines)}]"

        try:
            json.loads(fixed_string)
            return fixed_string, True
        except json.JSONDecodeError:
            return "", False
    else:
        return json_string, False


def add_tools_to_prompt(messages: list, functions: list):
    function_prompt = """Produce JSON OUTPUT ONLY! Adhere to this format {"name": "function_name", "arguments":{"argument_name": "argument_value"}} The following functions are available to you:"""
    # function_prompt = """You must return only one of these formats: (1) ONLY TEXT, no JSON, if you have already called the necessary functions or (2) ONLY JSON, no code/results/verbiage, if using a tool/function and it must adhere to this format {"name": "function_name", "arguments":{"argument_name": "argument_value"}} . The following functions are available to you:"""
    for function in functions:
        function_prompt += f"""\n{function}\n"""

    function_added_to_prompt = False
    for message in messages:
        if "system" in message["role"]:
            message["content"] += f""" {function_prompt}"""
            function_added_to_prompt = True
            break

    if not function_added_to_prompt:
        messages.append({"role": "system", "content": f"""{function_prompt}"""})

    return messages
