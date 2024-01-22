import asyncio
import inspect
import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


from autogen.agentchat.agent import Agent


class ToolUseMiddleware:
    """Middleware class for handling tool execution.

    This middleware handles tool execution on messages with OpenAI-compatible
    schema.

    Args:
        function_map (Dict[str, Callable]): Mapping function names
        to callable functions, also used for tool calls.

    """

    def __init__(self, function_map: Optional[Dict[str, Callable]] = None):
        if function_map is None:
            self._function_map = {}
        else:
            # Validate function names
            for name in function_map.keys():
                self._assert_valid_name(name)
            # Make a copy of the function map
            self._function_map = function_map.copy()

    def call(
        self,
        messages: List[Dict],
        sender: Optional[Agent] = None,
        next: Optional[Callable[..., Any]] = None,
    ) -> Union[str, Dict, None]:
        """Call the middleware.

        Args:
            messages (List[Dict]): the messages to be processed.
            sender (Optional[Agent]): the agent who sends the messages.
            next (Optional[Callable[..., Any]]): the next middleware to be called.

        Returns:
            Union[str, Dict, None]: the reply message.
        """
        message = messages[-1]
        if "function_call" in message and message["function_call"]:
            final, reply = self._generate_function_call_reply(message)
            if final:
                return reply
        if "tool_calls" in message and message["tool_calls"]:
            final, reply = self._generate_tool_calls_reply(message)
            if final:
                return reply
        return next(messages, sender)

    async def a_call(
        self,
        messages: List[Dict],
        sender: Optional[Agent] = None,
        next: Optional[Callable[..., Any]] = None,
    ) -> Union[str, Dict, None]:
        message = messages[-1]
        if "function_call" in message and message["function_call"]:
            final, reply = await self._a_generate_function_call_reply(message)
            if final:
                return reply
        if "tool_calls" in message and message["tool_calls"]:
            final, reply = await self._a_generate_tool_calls_reply(message)
            if final:
                return reply
        return await next(messages, sender)

    @property
    def function_map(self) -> Dict[str, Callable]:
        return self._function_map

    def register_function(self, function_map: Dict[str, Callable]):
        """Register functions to the middleware.

        Args:
            function_map: a dictionary mapping function names to functions.
        """
        for name in function_map.keys():
            self._assert_valid_name(name)
        self._function_map.update(function_map)

    def _generate_function_call_reply(self, message: Dict) -> Tuple[bool, Union[Dict, None]]:
        """
        Generate a reply using function call.

        "function_call" replaced by "tool_calls" as of [OpenAI API v1.1.0](https://github.com/openai/openai-python/releases/tag/v1.1.0)
        See https://platform.openai.com/docs/api-reference/chat/create#chat-create-functions
        """
        if "function_call" in message and message["function_call"]:
            func_call = message["function_call"]
            func = self._function_map.get(func_call.get("name", None), None)
            if inspect.iscoroutinefunction(func):
                return False, None
            _, func_return = self._execute_function(message["function_call"])
            return True, func_return
        return False, None

    async def _a_generate_function_call_reply(self, message: Dict) -> Tuple[bool, Union[Dict, None]]:
        """
        Generate a reply using async function call.

        "function_call" replaced by "tool_calls" as of [OpenAI API v1.1.0](https://github.com/openai/openai-python/releases/tag/v1.1.0)
        See https://platform.openai.com/docs/api-reference/chat/create#chat-create-functions
        """
        if "function_call" in message:
            func_call = message["function_call"]
            func_name = func_call.get("name", "")
            func = self._function_map.get(func_name, None)
            if func:
                if inspect.iscoroutinefunction(func):
                    _, func_return = await self._a_execute_function(func_call)
                else:
                    _, func_return = self._execute_function(func_call)
                return True, func_return
        return False, None

    def _generate_tool_calls_reply(self, message: List[Dict]) -> Tuple[bool, Union[Dict, None]]:
        """Generate a reply using tool call."""
        tool_returns = []
        for tool_call in message.get("tool_calls", []):
            id = tool_call["id"]
            function_call = tool_call.get("function", {})
            func = self._function_map.get(function_call.get("name", None), None)
            if inspect.iscoroutinefunction(func):
                continue
            _, func_return = self._execute_function(function_call)
            tool_returns.append(
                {
                    "tool_call_id": id,
                    "role": "tool",
                    "content": func_return.get("content", ""),
                }
            )
        if tool_returns:
            return True, {
                "role": "tool",
                "tool_responses": tool_returns,
                "content": "\n\n".join([self._str_for_tool_response(tool_return) for tool_return in tool_returns]),
            }
        return False, None

    async def _a_generate_tool_calls_reply(self, message: Dict) -> Tuple[bool, Union[Dict, None]]:
        """Generate a reply using async function call."""
        async_tool_calls = []
        for tool_call in message.get("tool_calls", []):
            async_tool_calls.append(self._a_execute_tool_call(tool_call))
        if async_tool_calls:
            tool_returns = await asyncio.gather(*async_tool_calls)
            return True, {
                "role": "tool",
                "tool_responses": tool_returns,
                "content": "\n\n".join([self._str_for_tool_response(tool_return) for tool_return in tool_returns]),
            }
        return False, None

    async def _a_execute_tool_call(self, tool_call):
        id = tool_call["id"]
        function_call = tool_call.get("function", {})
        _, func_return = await self._a_execute_function(function_call)
        return {
            "tool_call_id": id,
            "role": "tool",
            "content": func_return.get("content", ""),
        }

    def _execute_function(self, func_call, verbose: bool = False) -> Tuple[bool, Dict[str, str]]:
        """Execute a function call and return the result.

        Override this function to modify the way to execute function and tool calls.

        Args:
            func_call: a dictionary extracted from openai message at "function_call" or "tool_calls" with keys "name" and "arguments".

        Returns:
            A tuple of (is_exec_success, result_dict).
            is_exec_success (boolean): whether the execution is successful.
            result_dict: a dictionary with keys "name", "role", and "content". Value of "role" is "function".

        "function_call" deprecated as of [OpenAI API v1.1.0](https://github.com/openai/openai-python/releases/tag/v1.1.0)
        See https://platform.openai.com/docs/api-reference/chat/create#chat-create-function_call
        """
        func_name = func_call.get("name", "")
        func = self._function_map.get(func_name, None)

        is_exec_success = False
        if func is not None:
            # Extract arguments from a json-like string and put it into a dict.
            input_string = self._format_json_str(func_call.get("arguments", "{}"))
            try:
                arguments = json.loads(input_string)
            except json.JSONDecodeError as e:
                arguments = None
                content = f"Error: {e}\n You argument should follow json format."

            # Try to execute the function
            if arguments is not None:
                print(
                    colored(f"\n>>>>>>>> EXECUTING FUNCTION {func_name}...", "magenta"),
                    flush=True,
                )
                try:
                    content = func(**arguments)
                    is_exec_success = True
                except Exception as e:
                    content = f"Error: {e}"
        else:
            content = f"Error: Function {func_name} not found."

        if verbose:
            print(
                colored(f"\nInput arguments: {arguments}\nOutput:\n{content}", "magenta"),
                flush=True,
            )

        return is_exec_success, {
            "name": func_name,
            "role": "function",
            "content": str(content),
        }

    async def _a_execute_function(self, func_call):
        """Execute an async function call and return the result.

        Override this function to modify the way async functions and tools are executed.

        Args:
            func_call: a dictionary extracted from openai message at key "function_call" or "tool_calls" with keys "name" and "arguments".

        Returns:
            A tuple of (is_exec_success, result_dict).
            is_exec_success (boolean): whether the execution is successful.
            result_dict: a dictionary with keys "name", "role", and "content". Value of "role" is "function".

        "function_call" deprecated as of [OpenAI API v1.1.0](https://github.com/openai/openai-python/releases/tag/v1.1.0)
        See https://platform.openai.com/docs/api-reference/chat/create#chat-create-function_call
        """
        func_name = func_call.get("name", "")
        func = self._function_map.get(func_name, None)

        is_exec_success = False
        if func is not None:
            # Extract arguments from a json-like string and put it into a dict.
            input_string = self._format_json_str(func_call.get("arguments", "{}"))
            try:
                arguments = json.loads(input_string)
            except json.JSONDecodeError as e:
                arguments = None
                content = f"Error: {e}\n You argument should follow json format."

            # Try to execute the function
            if arguments is not None:
                print(
                    colored(f"\n>>>>>>>> EXECUTING ASYNC FUNCTION {func_name}...", "magenta"),
                    flush=True,
                )
                try:
                    if inspect.iscoroutinefunction(func):
                        content = await func(**arguments)
                    else:
                        # Fallback to sync function if the function is not async
                        content = func(**arguments)
                    is_exec_success = True
                except Exception as e:
                    content = f"Error: {e}"
        else:
            content = f"Error: Function {func_name} not found."

        return is_exec_success, {
            "name": func_name,
            "role": "function",
            "content": str(content),
        }

    def can_execute_function(self, name: Union[List[str], str]) -> bool:
        """Whether the agent can execute the function."""
        names = name if isinstance(name, list) else [name]
        return all([n in self._function_map for n in names])

    @staticmethod
    def _str_for_tool_response(tool_response):
        func_id = tool_response.get("tool_call_id", "")
        response = tool_response.get("content", "")
        return f"Tool Call Id: {func_id}\n{response}"

    @staticmethod
    def _assert_valid_name(name):
        """
        Ensure that configured names are valid, raises ValueError if not.

        For munging LLM responses use _normalize_name to ensure LLM specified names don't break the API.
        """
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            raise ValueError(f"Invalid name: {name}. Only letters, numbers, '_' and '-' are allowed.")
        if len(name) > 64:
            raise ValueError(f"Invalid name: {name}. Name must be less than 64 characters.")
        return name

    @staticmethod
    def _format_json_str(jstr):
        """Remove newlines outside of quotes, and handle JSON escape sequences.

        1. this function removes the newline in the query outside of quotes otherwise json.loads(s) will fail.
            Ex 1:
            "{\n"tool": "python",\n"query": "print('hello')\nprint('world')"\n}" -> "{"tool": "python","query": "print('hello')\nprint('world')"}"
            Ex 2:
            "{\n  \"location\": \"Boston, MA\"\n}" -> "{"location": "Boston, MA"}"

        2. this function also handles JSON escape sequences inside quotes,
            Ex 1:
            '{"args": "a\na\na\ta"}' -> '{"args": "a\\na\\na\\ta"}'
        """
        result = []
        inside_quotes = False
        last_char = " "
        for char in jstr:
            if last_char != "\\" and char == '"':
                inside_quotes = not inside_quotes
            last_char = char
            if not inside_quotes and char == "\n":
                continue
            if inside_quotes and char == "\n":
                char = "\\n"
            if inside_quotes and char == "\t":
                char = "\\t"
            result.append(char)
        return "".join(result)
