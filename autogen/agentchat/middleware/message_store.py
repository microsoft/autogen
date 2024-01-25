from collections import defaultdict
from typing import Any, Callable, DefaultDict, Dict, List, Optional, Union

from ...code_utils import content_str
from ...oai.client import OpenAIWrapper
from ...tty_utils import colored
from ..agent import Agent


class MessageStoreMiddleware:
    """A middleware that stores in-coming and out-going messages.

    This middleware handles messages with OpenAI-compatible schema.
    """

    def __init__(self, name: str, allow_format_str_template: bool = False) -> None:
        self._name = name
        self._oai_messages: DefaultDict[Agent, List[Dict[str, Optional[str]]]] = defaultdict(list)
        self._allow_format_str_template = allow_format_str_template

    def call(
        self,
        message: Union[Dict[str, Any], str],
        sender: Agent,
        request_reply: Optional[bool] = None,
        silent: bool = False,
        next: Optional[Callable[..., Any]] = None,
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """Call the middleware.

        Args:
            message (Union[Dict, str]): the message to be processed.
            sender (Agent): the sender of the message.
            request_reply (Optional[bool]): whether the sender requests a reply.
            silent (Optional[bool]): whether to print the message received.
            next (Optional[Callable[..., Any]]): the next middleware to be called.

        Returns:
            Union[str, Dict, None]: the reply message.
        """
        self._process_incoming_message(message, sender, silent)
        if request_reply is False:
            return None
        reply = next(message=message, sender=sender, request_reply=request_reply, silent=silent)  # type: ignore[misc]
        if reply is not None:
            self._process_outgoing_message(reply, sender, silent)
        return reply  # type: ignore[no-any-return]

    async def a_call(
        self,
        message: Union[Dict[str, Any], str],
        sender: Agent,
        request_reply: Optional[bool] = None,
        silent: bool = False,
        next: Optional[Callable[..., Any]] = None,
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """Call the middleware asynchronously.

        Args:
            message (Union[Dict, str]): the message to be processed.
            sender (Agent): the sender of the message.
            request_reply (Optional[bool]): whether the sender requests a reply.
            silent (Optional[bool]): whether to print the message received.
            next (Optional[Callable[..., Any]]): the next middleware to be called.

        Returns:
            Union[str, Dict, None]: the reply message.

        """
        self._process_incoming_message(message, sender, silent)
        if request_reply is False:
            return None
        reply = await next(message=message, sender=sender, request_reply=request_reply, silent=silent)  # type: ignore[misc]
        if reply is not None:
            self._process_outgoing_message(reply, sender, silent)
        return reply  # type: ignore[no-any-return]

    @property
    def oai_messages(self) -> DefaultDict[Agent, List[Dict[str, Optional[str]]]]:
        """The messages stored in the middleware.

        Returns:
            Dict[Agent, list]: the messages stored in the middleware, grouped by agent.
        """
        return self._oai_messages

    def clear_history(self, agent: Optional[Agent] = None) -> None:
        """Clear the chat history of the agent.

        Args:
            agent: the agent with whom the chat history to clear. If None, clear the chat history with all agents.
        """
        if agent is None:
            self._oai_messages.clear()
        else:
            self._oai_messages[agent].clear()

    def last_message(self, agent: Optional[Agent] = None) -> Optional[Dict[str, Optional[str]]]:
        """The last message exchanged with the agent.

        Args:
            agent (Agent): The agent in the conversation.
                If None and more than one agent's conversations are found, an error will be raised.
                If None and only one conversation is found, the last message of the only conversation will be returned.

        Returns:
            The last message exchanged with the agent.
        """
        if agent is None:
            n_conversations = len(self._oai_messages)
            if n_conversations == 0:
                return None
            if n_conversations == 1:
                for conversation in self._oai_messages.values():
                    return conversation[-1]
            raise ValueError("More than one conversation is found. Please specify the sender to get the last message.")
        if agent not in self._oai_messages.keys():
            raise KeyError(
                f"The agent '{agent.name}' is not present in any conversation. No history available for this agent."
            )
        return self._oai_messages[agent][-1]

    def _process_incoming_message(self, message: Union[Dict[str, Any], str], sender: Agent, silent: bool) -> None:
        # When the agent receives a message, the role of the message is "user". (If 'role' exists and is 'function', it will remain unchanged.)
        valid = self._append_oai_message(message, "user", sender)
        if not valid:
            raise ValueError(
                "Received message can't be converted into a valid ChatCompletion message. Either content or function_call must be provided."
            )
        if not silent:
            self._print_received_message(message, sender)

    def _process_outgoing_message(self, message: Union[Dict[str, Any], str], recipient: Agent, silent: bool) -> None:
        valid = self._append_oai_message(message, "assistant", recipient)
        if not valid:
            raise ValueError(
                "Reply message can't be converted into a valid ChatCompletion message. Either content or function_call must be provided."
            )

    def _append_oai_message(self, message: Union[Dict[str, Any], str], role: str, conversation_id: Agent) -> bool:
        """Append a message to the ChatCompletion conversation.

        If the message received is a string, it will be put in the "content" field of the new dictionary.
        If the message received is a dictionary but does not have any of the three fields "content", "function_call", or "tool_calls",
            this message is not a valid ChatCompletion message.
        If only "function_call" or "tool_calls" is provided, "content" will be set to None if not provided, and the role of the message will be forced "assistant".

        Args:
            message (dict or str): message to be appended to the ChatCompletion conversation.
            role (str): role of the message, can be "assistant" or "function".
            conversation_id (Agent): id of the conversation, should be the recipient or sender.

        Returns:
            bool: whether the message is appended to the ChatCompletion conversation.
        """
        message = self._message_to_dict(message)
        # create oai message to be appended to the oai conversation that can be passed to oai directly.
        oai_message = {
            k: message[k]
            for k in ("content", "function_call", "tool_calls", "tool_responses", "tool_call_id", "name", "context")
            if k in message and message[k] is not None
        }
        if "content" not in oai_message:
            if "function_call" in oai_message or "tool_calls" in oai_message:
                oai_message["content"] = None  # if only function_call is provided, content will be set to None.
            else:
                return False

        if message.get("role") in ["function", "tool"]:
            oai_message["role"] = message.get("role")
        else:
            oai_message["role"] = role

        if oai_message.get("function_call", False) or oai_message.get("tool_calls", False):
            oai_message["role"] = "assistant"  # only messages with role 'assistant' can have a function call.
        self._oai_messages[conversation_id].append(oai_message)
        return True

    @staticmethod
    def _message_to_dict(message: Union[Dict[str, Any], str]) -> Dict[str, Optional[str]]:
        """Convert a message to a dictionary.

        The message can be a string or a dictionary. The string will be put in
        the "content" field of the new dictionary.
        """
        if isinstance(message, str):
            return {"content": message}
        elif isinstance(message, dict):
            return message
        else:
            return dict(message)

    def _print_received_message(self, message: Union[Dict[str, Any], str], sender: Agent) -> None:
        # print the message received
        print(colored(sender.name, "yellow"), "(to", f"{self._name}):\n", flush=True)
        message = self._message_to_dict(message)

        if message.get("tool_responses"):  # Handle tool multi-call responses
            for tool_response in message["tool_responses"]:  # type: ignore[union-attr]
                self._print_received_message(tool_response, sender)
            if message.get("role") == "tool":
                return  # If role is tool, then content is just a concatenation of all tool_responses

        if message.get("role") in ["function", "tool"]:
            if message["role"] == "function":
                id_key = "name"
            else:
                id_key = "tool_call_id"

            func_print = f"***** Response from calling {message['role']} \"{message[id_key]}\" *****"
            print(colored(func_print, "green"), flush=True)
            print(message["content"], flush=True)
            print(colored("*" * len(func_print), "green"), flush=True)
        else:
            content = message.get("content")
            if content is not None:
                if "context" in message:
                    content = OpenAIWrapper.instantiate(content, message["context"], self._allow_format_str_template)  # type: ignore[arg-type]
                print(content_str(content), flush=True)
            if "function_call" in message and message["function_call"]:
                function_call: Dict[str, Any] = dict(message["function_call"])  # type: ignore[arg-type]
                func_print = (
                    f"***** Suggested function Call: {function_call.get('name', '(No function name found)')} *****"
                )
                print(colored(func_print, "green"), flush=True)
                print(
                    "Arguments: \n",
                    function_call.get("arguments", "(No arguments found)"),
                    flush=True,
                    sep="",
                )
                print(colored("*" * len(func_print), "green"), flush=True)
            if "tool_calls" in message and message["tool_calls"]:
                for tool_call in message["tool_calls"]:
                    id = tool_call.get("id", "(No id found)")  # type: ignore[attr-defined]
                    function_call = dict(tool_call.get("function", {}))  # type: ignore[attr-defined]
                    func_print = f"***** Suggested tool Call ({id}): {function_call.get('name', '(No function name found)')} *****"
                    print(colored(func_print, "green"), flush=True)
                    print(
                        "Arguments: \n",
                        function_call.get("arguments", "(No arguments found)"),
                        flush=True,
                        sep="",
                    )
                    print(colored("*" * len(func_print), "green"), flush=True)

        print("\n", "-" * 80, flush=True, sep="")
