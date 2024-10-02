"""Create an OpenAI-compatible client using Ollama's API.

Example:
    llm_config={
        "config_list": [{
            "api_type": "ollama",
            "model": "mistral:7b-instruct-v0.3-q6_K"
            }
    ]}

    agent = autogen.AssistantAgent("my_agent", llm_config=llm_config)

Install Ollama's python library using: pip install --upgrade ollama

Resources:
- https://github.com/ollama/ollama-python
"""

from __future__ import annotations

import copy
import json
import random
import re
import time
import warnings
from typing import Any, Dict, List, Tuple

import ollama
from fix_busted_json import repair_json
from ollama import Client
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage

from autogen.oai.client_utils import should_hide_tools, validate_parameter


class OllamaClient:
    """Client for Ollama's API."""

    # Defaults for manual tool calling
    # Instruction is added to the first system message and provides directions to follow a two step
    # process
    # 1. (before tools have been called) Return JSON with the functions to call
    # 2. (directly after tools have been called) Return Text describing the results of the function calls in text format

    # Override using "manual_tool_call_instruction" config parameter
    TOOL_CALL_MANUAL_INSTRUCTION = (
        "You are to follow a strict two step process that will occur over "
        "a number of interactions, so pay attention to what step you are in based on the full "
        "conversation. We will be taking turns so only do one step at a time so don't perform step "
        "2 until step 1 is complete and I've told you the result. The first step is to choose one "
        "or more functions based on the request given and return only JSON with the functions and "
        "arguments to use. The second step is to analyse the given output of the function and summarise "
        "it returning only TEXT and not Python or JSON. "
        "For argument values, be sure numbers aren't strings, they should not have double quotes around them. "
        "In terms of your response format, for step 1 return only JSON and NO OTHER text, "
        "for step 2 return only text and NO JSON/Python/Markdown. "
        'The format for running a function is [{"name": "function_name1", "arguments":{"argument_name": "argument_value"}},{"name": "function_name2", "arguments":{"argument_name": "argument_value"}}] '
        'Make sure the keys "name" and "arguments" are as described. '
        "If you don't get the format correct, try again. "
        "The following functions are available to you:[FUNCTIONS_LIST]"
    )

    # Appended to the last user message if no tools have been called
    # Override using "manual_tool_call_step1" config parameter
    TOOL_CALL_MANUAL_STEP1 = " (proceed with step 1)"

    # Appended to the user message after tools have been executed. Will create a 'user' message if one doesn't exist.
    # Override using "manual_tool_call_step2" config parameter
    TOOL_CALL_MANUAL_STEP2 = " (proceed with step 2)"

    def __init__(self, **kwargs):
        """Note that no api_key or environment variable is required for Ollama.

        Args:
            None
        """

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
        """Loads the parameters for Ollama API from the passed in parameters and returns a validated set. Checks types, ranges, and sets defaults"""
        ollama_params = {}

        # Check that we have what we need to use Ollama's API
        # https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-completion

        # The main parameters are model, prompt, stream, and options
        # Options is a dictionary of parameters for the model
        # There are other, advanced, parameters such as format, system (to override system message), template, raw, etc. - not used

        # We won't enforce the available models
        ollama_params["model"] = params.get("model", None)
        assert ollama_params[
            "model"
        ], "Please specify the 'model' in your config list entry to nominate the Ollama model to use."

        ollama_params["stream"] = validate_parameter(params, "stream", bool, True, False, None, None)

        # Build up the options dictionary
        # https://github.com/ollama/ollama/blob/main/docs/modelfile.md#valid-parameters-and-values
        options_dict = {}

        if "num_predict" in params:
            # Maximum number of tokens to predict, note: -1 is infinite, -2 is fill context, 128 is default
            options_dict["num_predict"] = validate_parameter(params, "num_predict", int, False, 128, None, None)

        if "repeat_penalty" in params:
            options_dict["repeat_penalty"] = validate_parameter(
                params, "repeat_penalty", (int, float), False, 1.1, None, None
            )

        if "seed" in params:
            options_dict["seed"] = validate_parameter(params, "seed", int, False, 42, None, None)

        if "temperature" in params:
            options_dict["temperature"] = validate_parameter(
                params, "temperature", (int, float), False, 0.8, None, None
            )

        if "top_k" in params:
            options_dict["top_k"] = validate_parameter(params, "top_k", int, False, 40, None, None)

        if "top_p" in params:
            options_dict["top_p"] = validate_parameter(params, "top_p", (int, float), False, 0.9, None, None)

        if self._native_tool_calls and self._tools_in_conversation and not self._should_hide_tools:
            ollama_params["tools"] = params["tools"]

            # Ollama doesn't support streaming with tools natively
            if ollama_params["stream"] and self._native_tool_calls:
                warnings.warn(
                    "Streaming is not supported when using tools and 'Native' tool calling, streaming will be disabled.",
                    UserWarning,
                )

                ollama_params["stream"] = False

        if not self._native_tool_calls and self._tools_in_conversation:
            # For manual tool calling we have injected the available tools into the prompt
            # and we don't want to force JSON mode
            ollama_params["format"] = ""  # Don't force JSON for manual tool calling mode

        if len(options_dict) != 0:
            ollama_params["options"] = options_dict

        return ollama_params

    def create(self, params: Dict) -> ChatCompletion:

        messages = params.get("messages", [])

        # Are tools involved in this conversation?
        self._tools_in_conversation = "tools" in params

        # We provide second-level filtering out of tools to avoid LLMs re-calling tools continuously
        if self._tools_in_conversation:
            hide_tools = validate_parameter(
                params, "hide_tools", str, False, "never", None, ["if_all_run", "if_any_run", "never"]
            )
            self._should_hide_tools = should_hide_tools(messages, params["tools"], hide_tools)
        else:
            self._should_hide_tools = False

        # Are we using native Ollama tool calling, otherwise we're doing manual tool calling
        # We allow the user to decide if they want to use Ollama's tool calling
        # or for tool calling to be handled manually through text messages
        # Default is True = Ollama's tool calling
        self._native_tool_calls = validate_parameter(params, "native_tool_calls", bool, False, True, None, None)

        if not self._native_tool_calls:
            # Load defaults
            self._manual_tool_call_instruction = validate_parameter(
                params, "manual_tool_call_instruction", str, False, self.TOOL_CALL_MANUAL_INSTRUCTION, None, None
            )
            self._manual_tool_call_step1 = validate_parameter(
                params, "manual_tool_call_step1", str, False, self.TOOL_CALL_MANUAL_STEP1, None, None
            )
            self._manual_tool_call_step2 = validate_parameter(
                params, "manual_tool_call_step2", str, False, self.TOOL_CALL_MANUAL_STEP2, None, None
            )

        # Convert AutoGen messages to Ollama messages
        ollama_messages = self.oai_messages_to_ollama_messages(
            messages,
            (
                params["tools"]
                if (not self._native_tool_calls and self._tools_in_conversation) and not self._should_hide_tools
                else None
            ),
        )

        # Parse parameters to the Ollama API's parameters
        ollama_params = self.parse_params(params)

        ollama_params["messages"] = ollama_messages

        # Token counts will be returned
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        ans = None
        try:
            if "client_host" in params:
                client = Client(host=params["client_host"])
                response = client.chat(**ollama_params)
            else:
                response = ollama.chat(**ollama_params)
        except Exception as e:
            raise RuntimeError(f"Ollama exception occurred: {e}")
        else:

            if ollama_params["stream"]:
                # Read in the chunks as they stream, taking in tool_calls which may be across
                # multiple chunks if more than one suggested
                ans = ""
                for chunk in response:
                    ans = ans + (chunk["message"]["content"] or "")

                    if "done_reason" in chunk:
                        prompt_tokens = chunk["prompt_eval_count"] if "prompt_eval_count" in chunk else 0
                        completion_tokens = chunk["eval_count"] if "eval_count" in chunk else 0
                        total_tokens = prompt_tokens + completion_tokens
            else:
                # Non-streaming finished
                ans: str = response["message"]["content"]

                prompt_tokens = response["prompt_eval_count"] if "prompt_eval_count" in response else 0
                completion_tokens = response["eval_count"] if "eval_count" in response else 0
                total_tokens = prompt_tokens + completion_tokens

        if response is not None:

            # Defaults
            ollama_finish = "stop"
            tool_calls = None

            # Id and streaming text into response
            if ollama_params["stream"]:
                response_content = ans
                response_id = chunk["created_at"]
            else:
                response_content = response["message"]["content"]
                response_id = response["created_at"]

            # Process tools in the response
            if self._tools_in_conversation:

                if self._native_tool_calls:

                    if not ollama_params["stream"]:
                        response_content = response["message"]["content"]

                        # Native tool calling
                        if "tool_calls" in response["message"]:
                            ollama_finish = "tool_calls"
                            tool_calls = []
                            random_id = random.randint(0, 10000)
                            for tool_call in response["message"]["tool_calls"]:
                                tool_calls.append(
                                    ChatCompletionMessageToolCall(
                                        id="ollama_func_{}".format(random_id),
                                        function={
                                            "name": tool_call["function"]["name"],
                                            "arguments": json.dumps(tool_call["function"]["arguments"]),
                                        },
                                        type="function",
                                    )
                                )

                                random_id += 1

                elif not self._native_tool_calls:

                    # Try to convert the response to a tool call object
                    response_toolcalls = response_to_tool_call(ans)

                    # If we can, then we've got tool call(s)
                    if response_toolcalls is not None:
                        ollama_finish = "tool_calls"
                        tool_calls = []
                        random_id = random.randint(0, 10000)

                        for json_function in response_toolcalls:
                            tool_calls.append(
                                ChatCompletionMessageToolCall(
                                    id="ollama_manual_func_{}".format(random_id),
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

                        # Blank the message content
                        response_content = ""

        else:
            raise RuntimeError("Failed to get response from Ollama.")

        # Convert response to AutoGen response
        message = ChatCompletionMessage(
            role="assistant",
            content=response_content,
            function_call=None,
            tool_calls=tool_calls,
        )
        choices = [Choice(finish_reason=ollama_finish, index=0, message=message)]

        response_oai = ChatCompletion(
            id=response_id,
            model=ollama_params["model"],
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

    def oai_messages_to_ollama_messages(self, messages: list[Dict[str, Any]], tools: list) -> list[dict[str, Any]]:
        """Convert messages from OAI format to Ollama's format.
        We correct for any specific role orders and types, and convert tools to messages (as Ollama can't use tool messages)
        """

        ollama_messages = copy.deepcopy(messages)

        # Remove the name field
        for message in ollama_messages:
            if "name" in message:
                message.pop("name", None)

        # Having a 'system' message on the end does not work well with Ollama, so we change it to 'user'
        # 'system' messages on the end are typical of the summarisation message: summary_method="reflection_with_llm"
        if len(ollama_messages) > 1 and ollama_messages[-1]["role"] == "system":
            ollama_messages[-1]["role"] = "user"

        # Process messages for tool calling manually
        if tools is not None and not self._native_tool_calls:
            # 1. We need to append instructions to the starting system message on function calling
            # 2. If we have not yet called tools we append "step 1 instruction" to the latest user message
            # 3. If we have already called tools we append "step 2 instruction" to the latest user message

            have_tool_calls = False
            have_tool_results = False
            last_tool_result_index = -1

            for i, message in enumerate(ollama_messages):
                if "tool_calls" in message:
                    have_tool_calls = True
                if "tool_call_id" in message:
                    have_tool_results = True
                    last_tool_result_index = i

            tool_result_is_last_msg = have_tool_results and last_tool_result_index == len(ollama_messages) - 1

            if ollama_messages[0]["role"] == "system":
                manual_instruction = self._manual_tool_call_instruction

                # Build a string of the functions available
                functions_string = ""
                for function in tools:
                    functions_string += f"""\n{function}\n"""

                # Replace single quotes with double questions - Not sure why this helps the LLM perform
                # better, but it seems to. Monitor and remove if not necessary.
                functions_string = functions_string.replace("'", '"')

                manual_instruction = manual_instruction.replace("[FUNCTIONS_LIST]", functions_string)

                # Update the system message with the instructions and functions
                ollama_messages[0]["content"] = ollama_messages[0]["content"] + manual_instruction.rstrip()

            # If we are still in the function calling or evaluating process, append the steps instruction
            if not have_tool_calls or tool_result_is_last_msg:
                if ollama_messages[0]["role"] == "system":
                    # NOTE: we require a system message to exist for the manual steps texts
                    # Append the manual step instructions
                    content_to_append = (
                        self._manual_tool_call_step1 if not have_tool_results else self._manual_tool_call_step2
                    )

                    if content_to_append != "":
                        # Append the relevant tool call instruction to the latest user message
                        if ollama_messages[-1]["role"] == "user":
                            ollama_messages[-1]["content"] = ollama_messages[-1]["content"] + content_to_append
                        else:
                            ollama_messages.append({"role": "user", "content": content_to_append})

        # Convert tool call and tool result messages to normal text messages for Ollama
        for i, message in enumerate(ollama_messages):
            if "tool_calls" in message:
                # Recommended tool calls
                content = "Run the following function(s):"
                for tool_call in message["tool_calls"]:
                    content = content + "\n" + str(tool_call)
                ollama_messages[i] = {"role": "assistant", "content": content}
            if "tool_call_id" in message:
                # Executed tool results
                message["result"] = message["content"]
                del message["content"]
                del message["role"]
                content = "The following function was run: " + str(message)
                ollama_messages[i] = {"role": "user", "content": content}

        # As we are changing messages, let's merge if they have two user messages on the end and the last one is tool call step instructions
        if (
            len(ollama_messages) >= 2
            and not self._native_tool_calls
            and ollama_messages[-2]["role"] == "user"
            and ollama_messages[-1]["role"] == "user"
            and (
                ollama_messages[-1]["content"] == self._manual_tool_call_step1
                or ollama_messages[-1]["content"] == self._manual_tool_call_step2
            )
        ):
            ollama_messages[-2]["content"] = ollama_messages[-2]["content"] + ollama_messages[-1]["content"]
            del ollama_messages[-1]

        # Ensure the last message is a user / system message, if not, add a user message
        if ollama_messages[-1]["role"] != "user" and ollama_messages[-1]["role"] != "system":
            ollama_messages.append({"role": "user", "content": "Please continue."})

        return ollama_messages


def response_to_tool_call(response_string: str) -> Any:
    """Attempts to convert the response to an object, aimed to align with function format [{},{}]"""

    # We try and detect the list[dict] format:
    # Pattern 1 is [{},{}]
    # Pattern 2 is {} (without the [], so could be a single function call)
    patterns = [r"\[[\s\S]*?\]", r"\{[\s\S]*\}"]

    for i, pattern in enumerate(patterns):
        # Search for the pattern in the input string
        matches = re.findall(pattern, response_string.strip())

        for match in matches:

            # It has matched, extract it and load it
            json_str = match.strip()
            data_object = None

            try:
                # Attempt to convert it as is
                data_object = json.loads(json_str)
            except Exception:
                try:
                    # If that fails, attempt to repair it

                    if i == 0:
                        # Enclose to a JSON object for repairing, which is restored upon fix
                        fixed_json = repair_json("{'temp':" + json_str + "}")
                        data_object = json.loads(fixed_json)
                        data_object = data_object["temp"]
                    else:
                        fixed_json = repair_json(json_str)
                        data_object = json.loads(fixed_json)
                except json.JSONDecodeError as e:
                    if e.msg == "Invalid \\escape":
                        # Handle Mistral/Mixtral trying to escape underlines with \\
                        try:
                            json_str = json_str.replace("\\_", "_")
                            if i == 0:
                                fixed_json = repair_json("{'temp':" + json_str + "}")
                                data_object = json.loads(fixed_json)
                                data_object = data_object["temp"]
                            else:
                                fixed_json = repair_json("{'temp':" + json_str + "}")
                                data_object = json.loads(fixed_json)
                        except Exception:
                            pass
                except Exception:
                    pass

            if data_object is not None:
                data_object = _object_to_tool_call(data_object)

                if data_object is not None:
                    return data_object

    # There's no tool call in the response
    return None


def _object_to_tool_call(data_object: Any) -> List[Dict]:
    """Attempts to convert an object to a valid tool call object List[Dict] and returns it, if it can, otherwise None"""

    # If it's a dictionary and not a list then wrap in a list
    if isinstance(data_object, dict):
        data_object = [data_object]

    # Validate that the data is a list of dictionaries
    if isinstance(data_object, list) and all(isinstance(item, dict) for item in data_object):
        # Perfect format, a list of dictionaries

        # Check that each dictionary has at least 'name', optionally 'arguments' and no other keys
        is_invalid = False
        for item in data_object:
            if not is_valid_tool_call_item(item):
                is_invalid = True
                break

        # All passed, name and (optionally) arguments exist for all entries.
        if not is_invalid:
            return data_object
    elif isinstance(data_object, list):
        # If it's a list but the items are not dictionaries, check if they are strings that can be converted to dictionaries
        data_copy = data_object.copy()
        is_invalid = False
        for i, item in enumerate(data_copy):
            try:
                new_item = eval(item)
                if isinstance(new_item, dict):
                    if is_valid_tool_call_item(new_item):
                        data_object[i] = new_item
                    else:
                        is_invalid = True
                        break
                else:
                    is_invalid = True
                    break
            except Exception:
                is_invalid = True
                break

        if not is_invalid:
            return data_object

    return None


def is_valid_tool_call_item(call_item: dict) -> bool:
    """Check that a dictionary item has at least 'name', optionally 'arguments' and no other keys to match a tool call JSON"""
    if "name" not in call_item or not isinstance(call_item["name"], str):
        return False

    if set(call_item.keys()) - {"name", "arguments"}:
        return False

    return True
