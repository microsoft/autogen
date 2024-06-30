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

    # Defaults for manual tool calling
    # Instruction is added to the first system message and provides directions to follow a two step
    # process
    # 1. (before tools have been called) Return JSON with the functions to call
    # 2. (directly after tools have been called) Return Text describing the results of the function calls in text format
    TOOL_CALL_MANUAL_INSTRUCTION = (
        "You are to follow a strict two step process that will occur over "
        "a number of interactions, so pay attention to what step you are in based on the full "
        "conversation. We will be taking turns so only do one step at a time so don't perform step "
        "2 until step 1 is complete and I've told you the result. The first step is to choose one "
        "or more functions based on the request given and return only JSON with the functions and "
        "arguments to use. The second step is to analyse the given output of the function and summarise "
        "it returning only TEXT and not Python or JSON. "
        "In terms of your response format, for step 1 return only JSON and NO OTHER text, "
        "for step 2 return only text and NO JSON/Python/Markdown. "
        'The format for running a function is [{"name": "function_name1", "arguments":{"argument_name": "argument_value"}},{"name": "function_name2", "arguments":{"argument_name": "argument_value"}}] and if there are no arguments then return an empty set of arguments '
        "The following functions are available to you:\n[FUNCTIONS_LIST]"
    )

    # Appended to the last user message if no tools have been called
    TOOL_CALL_MANUAL_STEP1 = """ (proceed with step 1)"""

    # Appended to the user message after tools have been executed. Will create a 'user' message if one doesn't exist.
    TOOL_CALL_MANUAL_STEP2 = """ (proceed with step 2)"""

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

        # Are tools involved in this conversation?
        self._tools_in_conversation = "tools" in params

        # Function/Tool calling options
        # 'default' = uses LiteLLM function calling mode
        # 'manual' injects directions, functions into system prompt, 2-step process for LLM to follow
        self._tool_calling_mode = validate_parameter(
            params, "tool_calling_mode", str, False, "default", None, ["default", "manual"]
        )

        # Convert AutoGen messages to LiteLLM messages
        litellm_messages = self.oai_messages_to_litellm_messages(
            messages, params["tools"] if self._tools_in_conversation else None
        )

        # Parse parameters to the Groq API's parameters
        litellm_params = self.parse_params(params)

        # Add tools to the call if we have them and aren't hiding them
        if self._tools_in_conversation:
            if self._tool_calling_mode == "default":
                hide_tools = validate_parameter(
                    params, "hide_tools", str, False, "never", None, ["if_all_run", "if_any_run", "never"]
                )
                if not should_hide_tools(litellm_messages, params["tools"], hide_tools):
                    # LiteLLMs standard tools support
                    litellm_params["tools"] = params["tools"]
            else:
                litellm_params["format"] = ""  # Don't force JSON for manual tool calling mode

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
                # Non-streaming response

                if response.choices[0].finish_reason == "tool_calls":
                    # LiteLLM default tool calling
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

                    # Blank the message content
                    response_content = ""
                else:
                    # Not returned as a tool_call, but could be a text response
                    # with tool calling if we're using 'manual' tool_calling_mode
                    is_manual_tool_calling = False

                    if self._tools_in_conversation and self._tool_calling_mode == "manual":
                        # Try to convert the response to a tool call object
                        response_toolcalls = response_to_object(ans)

                        # If we can, then it's a manual tool call
                        if response_toolcalls is not None:
                            litellm_finish = "tool_calls"
                            tool_calls = []
                            random_id = random.randint(0, 10000)

                            for json_function in response_toolcalls:
                                tool_calls.append(
                                    ChatCompletionMessageToolCall(
                                        id="litellm_func_{}".format(random_id),
                                        function={
                                            "name": json_function["name"],
                                            "arguments": (
                                                json.dumps(json_function["arguments"])
                                                if "arguments" in json_function
                                                else "{}"
                                            ),
                                        },
                                        type="function",
                                    )
                                )

                                random_id += 1

                            is_manual_tool_calling = True

                            # Blank the message content
                            response_content = ""

                    if not is_manual_tool_calling:
                        response_content = response.choices[0].message.content
                        litellm_finish = "stop"
                        tool_calls = None

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

    def oai_messages_to_litellm_messages(self, messages: list[Dict[str, Any]], tools: list) -> list[dict[str, Any]]:
        """Convert messages from OAI format to LiteLLM's format.
        We correct for any specific role orders and types.
        """

        # IMPORTANT NOTE: LiteLLM's Ollama library changes 'tool' roles to 'assistant'

        litellm_messages = copy.deepcopy(messages)

        # Remove the name field
        for message in litellm_messages:
            if "name" in message:
                message.pop("name", None)

        # Process messages for tool calling manually
        if self._tools_in_conversation and self._tool_calling_mode == "manual":
            # 1. We need to append instructions to the starting system message on function calling
            # 2. If we have not yet called tools we append "step 1 instruction" to the latest user message
            # 3. If we have already called tools we append "step 2 instruction" to the latest user message

            have_tool_calls = False
            have_tool_results = False
            last_tool_result_index = -1

            for i, message in enumerate(litellm_messages):
                if "tool_calls" in message:
                    have_tool_calls = True
                if "tool_call_id" in message:
                    have_tool_results = True
                    last_tool_result_index = i

            tool_result_is_last_msg = have_tool_results and last_tool_result_index == len(litellm_messages) - 1

            # If we are still in the function calling or evaluating process, append the steps instruction
            if not have_tool_calls or tool_result_is_last_msg:
                if litellm_messages[0]["role"] == "system":
                    manual_instruction = self.TOOL_CALL_MANUAL_INSTRUCTION

                    # Build a string of the functions available
                    functions_string = ""
                    for function in tools:
                        functions_string += f"""\n{function}\n"""

                    # Replace single quotes with double questions - Not sure why this helps the LLM perform
                    # better, but it seems to. Monitor and remove if not necessary.
                    functions_string = functions_string.replace("'", '"')

                    manual_instruction = manual_instruction.replace("[FUNCTIONS_LIST]", functions_string)

                    # Update the system message with the instructions and functions
                    litellm_messages[0]["content"] = litellm_messages[0]["content"] + manual_instruction.rstrip()

                # Append the manual step instructions
                content_to_append = (
                    self.TOOL_CALL_MANUAL_STEP1 if not have_tool_results else self.TOOL_CALL_MANUAL_STEP2
                )

                # Append the relevant tool call instruction to the latest user message
                if litellm_messages[-1]["role"] == "user":
                    litellm_messages[-1]["content"] = litellm_messages[-1]["content"] + content_to_append
                else:
                    litellm_messages.append({"role": "user", "content": content_to_append})

        # Ensure the last message is a user message, if not, add a user message
        if litellm_messages[-1]["role"] != "user":
            litellm_messages.append({"role": "user", "content": "Please continue."})

        return litellm_messages


def response_to_object(response_string: str) -> Any:
    """Attempts to convert the response to an object, aimed to align with function format [{},{}]"""
    try:
        data_object = eval(response_string.strip())

        # Validate that the data is a list of dictionaries
        if isinstance(data_object, list) and all(isinstance(item, dict) for item in data_object):
            return data_object
        else:
            # print("Invalid data format: Must be a list of dictionaries.")
            return None
    except (SyntaxError, NameError, TypeError):
        return None

    return None
