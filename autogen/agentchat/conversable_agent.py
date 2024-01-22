import asyncio
import copy
import functools
import inspect
import json
import logging
import re
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union

from .. import OpenAIWrapper
from ..cache.cache import Cache
from ..code_utils import (
    DEFAULT_MODEL,
    UNKNOWN,
    content_str,
    check_can_use_docker_or_throw,
    decide_use_docker,
    execute_code,
    extract_code,
    infer_lang,
)


from ..function_utils import get_function_schema, load_basemodels_if_needed, serialize_to_str
from .agent import Agent
from .._pydantic import model_dump

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


__all__ = ("ConversableAgent",)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class ConversableAgent(Agent):
    """(In preview) A class for generic conversable agents which can be configured as assistant or user proxy.

    After receiving each message, the agent will send a reply to the sender unless the msg is a termination msg.
    For example, AssistantAgent and UserProxyAgent are subclasses of this class,
    configured with different default settings.

    To modify auto reply, override `generate_reply` method.
    To disable/enable human response in every turn, set `human_input_mode` to "NEVER" or "ALWAYS".
    To modify the way to get human input, override `get_human_input` method.
    To modify the way to execute code blocks, single code block, or function call, override `execute_code_blocks`,
    `run_code`, and `execute_function` methods respectively.
    To customize the initial message when a conversation starts, override `generate_init_message` method.
    """

    DEFAULT_CONFIG = {}  # An empty configuration
    MAX_CONSECUTIVE_AUTO_REPLY = 100  # maximum number of consecutive auto replies (subject to future change)

    llm_config: Union[Dict, Literal[False]]

    def __init__(
        self,
        name: str,
        system_message: Optional[Union[str, List]] = "You are a helpful AI Assistant.",
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Optional[Union[Dict, Literal[False]]] = None,
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        description: Optional[str] = None,
    ):
        """
        Args:
            name (str): name of the agent.
            system_message (str or list): system message for the ChatCompletion inference.
            is_termination_msg (function): a function that takes a message in the form of a dictionary
                and returns a boolean value indicating if this received message is a termination message.
                The dict can contain the following keys: "content", "role", "name", "function_call".
            max_consecutive_auto_reply (int): the maximum number of consecutive auto replies.
                default to None (no limit provided, class attribute MAX_CONSECUTIVE_AUTO_REPLY will be used as the limit in this case).
                When set to 0, no auto reply will be generated.
            human_input_mode (str): whether to ask for human inputs every time a message is received.
                Possible values are "ALWAYS", "TERMINATE", "NEVER".
                (1) When "ALWAYS", the agent prompts for human input every time a message is received.
                    Under this mode, the conversation stops when the human input is "exit",
                    or when is_termination_msg is True and there is no human input.
                (2) When "TERMINATE", the agent only prompts for human input only when a termination message is received or
                    the number of auto reply reaches the max_consecutive_auto_reply.
                (3) When "NEVER", the agent will never prompt for human input. Under this mode, the conversation stops
                    when the number of auto reply reaches the max_consecutive_auto_reply or when is_termination_msg is True.
            function_map (dict[str, callable]): Mapping function names (passed to openai) to callable functions, also used for tool calls.
            code_execution_config (dict or False): config for the code execution.
                To disable code execution, set to False. Otherwise, set to a dictionary with the following keys:
                - work_dir (Optional, str): The working directory for the code execution.
                    If None, a default working directory will be used.
                    The default working directory is the "extensions" directory under
                    "path_to_autogen".
                - use_docker (Optional, list, str or bool): The docker image to use for code execution.
                    Default is True, which means the code will be executed in a docker container. A default list of images will be used.
                    If a list or a str of image name(s) is provided, the code will be executed in a docker container
                    with the first image successfully pulled.
                    If False, the code will be executed in the current environment.
                    We strongly recommend using docker for code execution.
                - timeout (Optional, int): The maximum execution time in seconds.
                - last_n_messages (Experimental, Optional, int or str): The number of messages to look back for code execution. If set to 'auto', it will scan backwards through all messages arriving since the agent last spoke, which is typically the last time execution was attempted. (Default: auto)
            llm_config (dict or False): llm inference configuration.
                Please refer to [OpenAIWrapper.create](/docs/reference/oai/client#create)
                for available options.
                To disable llm-based auto reply, set to False.
            default_auto_reply (str or dict or None): default auto reply when no code execution or llm-based reply is generated.
            description (str): a short description of the agent. This description is used by other agents
                (e.g. the GroupChatManager) to decide when to call upon this agent. (Default: system_message)
        """
        super().__init__(name)
        # a dictionary of conversations, default value is list
        self._oai_messages = defaultdict(list)
        self._oai_system_message = [{"content": system_message, "role": "system"}]
        self.description = description if description is not None else system_message
        self._is_termination_msg = (
            is_termination_msg
            if is_termination_msg is not None
            else (lambda x: content_str(x.get("content")) == "TERMINATE")
        )

        if llm_config is False:
            self.llm_config = False
            self.client = None
        else:
            self.llm_config = self.DEFAULT_CONFIG.copy()
            if isinstance(llm_config, dict):
                self.llm_config.update(llm_config)
            self.client = OpenAIWrapper(**self.llm_config)

        # Initialize standalone client cache object.
        self.client_cache = None

        self._code_execution_config: Union[Dict, Literal[False]] = (
            {} if code_execution_config is None else code_execution_config
        )

        if isinstance(self._code_execution_config, dict):
            use_docker = self._code_execution_config.get("use_docker", None)
            use_docker = decide_use_docker(use_docker)
            check_can_use_docker_or_throw(use_docker)
            self._code_execution_config["use_docker"] = use_docker

        self.human_input_mode = human_input_mode
        self._max_consecutive_auto_reply = (
            max_consecutive_auto_reply if max_consecutive_auto_reply is not None else self.MAX_CONSECUTIVE_AUTO_REPLY
        )
        self._consecutive_auto_reply_counter = defaultdict(int)
        self._max_consecutive_auto_reply_dict = defaultdict(self.max_consecutive_auto_reply)
        self._function_map = (
            {}
            if function_map is None
            else {name: callable for name, callable in function_map.items() if self._assert_valid_name(name)}
        )
        self._default_auto_reply = default_auto_reply
        self._reply_func_list = []
        self._ignore_async_func_in_sync_chat_list = []
        self.reply_at_receive = defaultdict(bool)
        self.register_reply([Agent, None], ConversableAgent.generate_oai_reply)
        self.register_reply([Agent, None], ConversableAgent.a_generate_oai_reply, ignore_async_in_sync_chat=True)
        self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_tool_calls_reply)
        self.register_reply([Agent, None], ConversableAgent.a_generate_tool_calls_reply, ignore_async_in_sync_chat=True)
        self.register_reply([Agent, None], ConversableAgent.generate_function_call_reply)
        self.register_reply(
            [Agent, None], ConversableAgent.a_generate_function_call_reply, ignore_async_in_sync_chat=True
        )
        self.register_reply([Agent, None], ConversableAgent.check_termination_and_human_reply)
        self.register_reply(
            [Agent, None], ConversableAgent.a_check_termination_and_human_reply, ignore_async_in_sync_chat=True
        )

        # Registered hooks are kept in lists, indexed by hookable method, to be called in their order of registration.
        # New hookable methods should be added to this list as required to support new agent capabilities.
        self.hook_lists = {self.process_last_message: []}  # This is currently the only hookable method.

    def register_reply(
        self,
        trigger: Union[Type[Agent], str, Agent, Callable[[Agent], bool], List],
        reply_func: Callable,
        position: int = 0,
        config: Optional[Any] = None,
        reset_config: Optional[Callable] = None,
        *,
        ignore_async_in_sync_chat: bool = False,
    ):
        """Register a reply function.

        The reply function will be called when the trigger matches the sender.
        The function registered later will be checked earlier by default.
        To change the order, set the position to a positive integer.

        Both sync and async reply functions can be registered. The sync reply function will be triggered
        from both sync and async chats. However, an async reply function will only be triggered from async
        chats (initiated with `ConversableAgent.a_initiate_chat`). If an `async` reply function is registered
        and a chat is initialized with a sync function, `ignore_async_in_sync_chat` determines the behaviour as follows:
        - if `ignore_async_in_sync_chat` is set to `False` (default value), an exception will be raised, and
        - if `ignore_async_in_sync_chat` is set to `True`, the reply function will be ignored.

        Args:
            trigger (Agent class, str, Agent instance, callable, or list): the trigger.
                - If a class is provided, the reply function will be called when the sender is an instance of the class.
                - If a string is provided, the reply function will be called when the sender's name matches the string.
                - If an agent instance is provided, the reply function will be called when the sender is the agent instance.
                - If a callable is provided, the reply function will be called when the callable returns True.
                - If a list is provided, the reply function will be called when any of the triggers in the list is activated.
                - If None is provided, the reply function will be called only when the sender is None.
                Note: Be sure to register `None` as a trigger if you would like to trigger an auto-reply function with non-empty messages and `sender=None`.
            reply_func (Callable): the reply function.
                The function takes a recipient agent, a list of messages, a sender agent and a config as input and returns a reply message.
            position: the position of the reply function in the reply function list.
            config: the config to be passed to the reply function, see below.
            reset_config: the function to reset the config, see below.
            ignore_async_in_sync_chat: whether to ignore the async reply function in sync chats. If `False`, an exception
                will be raised if an async reply function is registered and a chat is initialized with a sync
                function.
        ```python
        def reply_func(
            recipient: ConversableAgent,
            messages: Optional[List[Dict]] = None,
            sender: Optional[Agent] = None,
            config: Optional[Any] = None,
        ) -> Tuple[bool, Union[str, Dict, None]]:
        ```
            position (int): the position of the reply function in the reply function list.
                The function registered later will be checked earlier by default.
                To change the order, set the position to a positive integer.
            config (Any): the config to be passed to the reply function.
                When an agent is reset, the config will be reset to the original value.
            reset_config (Callable): the function to reset the config.
                The function returns None. Signature: ```def reset_config(config: Any)```
        """
        if not isinstance(trigger, (type, str, Agent, Callable, list)):
            raise ValueError("trigger must be a class, a string, an agent, a callable or a list.")
        self._reply_func_list.insert(
            position,
            {
                "trigger": trigger,
                "reply_func": reply_func,
                "config": copy.copy(config),
                "init_config": config,
                "reset_config": reset_config,
            },
        )
        if ignore_async_in_sync_chat and inspect.iscoroutinefunction(reply_func):
            self._ignore_async_func_in_sync_chat_list.append(reply_func)

    @property
    def system_message(self) -> Union[str, List]:
        """Return the system message."""
        return self._oai_system_message[0]["content"]

    def update_system_message(self, system_message: Union[str, List]):
        """Update the system message.

        Args:
            system_message (str or List): system message for the ChatCompletion inference.
        """
        self._oai_system_message[0]["content"] = system_message

    def update_max_consecutive_auto_reply(self, value: int, sender: Optional[Agent] = None):
        """Update the maximum number of consecutive auto replies.

        Args:
            value (int): the maximum number of consecutive auto replies.
            sender (Agent): when the sender is provided, only update the max_consecutive_auto_reply for that sender.
        """
        if sender is None:
            self._max_consecutive_auto_reply = value
            for k in self._max_consecutive_auto_reply_dict:
                self._max_consecutive_auto_reply_dict[k] = value
        else:
            self._max_consecutive_auto_reply_dict[sender] = value

    def max_consecutive_auto_reply(self, sender: Optional[Agent] = None) -> int:
        """The maximum number of consecutive auto replies."""
        return self._max_consecutive_auto_reply if sender is None else self._max_consecutive_auto_reply_dict[sender]

    @property
    def chat_messages(self) -> Dict[Agent, List[Dict]]:
        """A dictionary of conversations from agent to list of messages."""
        return self._oai_messages

    def last_message(self, agent: Optional[Agent] = None) -> Optional[Dict]:
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

    @property
    def use_docker(self) -> Union[bool, str, None]:
        """Bool value of whether to use docker to execute the code,
        or str value of the docker image name to use, or None when code execution is disabled.
        """
        return None if self._code_execution_config is False else self._code_execution_config.get("use_docker")

    @staticmethod
    def _message_to_dict(message: Union[Dict, str]) -> Dict:
        """Convert a message to a dictionary.

        The message can be a string or a dictionary. The string will be put in the "content" field of the new dictionary.
        """
        if isinstance(message, str):
            return {"content": message}
        elif isinstance(message, dict):
            return message
        else:
            return dict(message)

    @staticmethod
    def _normalize_name(name):
        """
        LLMs sometimes ask functions while ignoring their own format requirements, this function should be used to replace invalid characters with "_".

        Prefer _assert_valid_name for validating user configuration or input
        """
        return re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:64]

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

    def _append_oai_message(self, message: Union[Dict, str], role, conversation_id: Agent) -> bool:
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

    def send(
        self,
        message: Union[Dict, str],
        recipient: Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        """Send a message to another agent.

        Args:
            message (dict or str): message to be sent.
                The message could contain the following fields:
                - content (str or List): Required, the content of the message. (Can be None)
                - function_call (str): the name of the function to be called.
                - name (str): the name of the function to be called.
                - role (str): the role of the message, any role that is not "function"
                    will be modified to "assistant".
                - context (dict): the context of the message, which will be passed to
                    [OpenAIWrapper.create](../oai/client#create).
                    For example, one agent can send a message A as:
        ```python
        {
            "content": lambda context: context["use_tool_msg"],
            "context": {
                "use_tool_msg": "Use tool X if they are relevant."
            }
        }
        ```
                    Next time, one agent can send a message B with a different "use_tool_msg".
                    Then the content of message A will be refreshed to the new "use_tool_msg".
                    So effectively, this provides a way for an agent to send a "link" and modify
                    the content of the "link" later.
            recipient (Agent): the recipient of the message.
            request_reply (bool or None): whether to request a reply from the recipient.
            silent (bool or None): (Experimental) whether to print the message sent.

        Raises:
            ValueError: if the message can't be converted into a valid ChatCompletion message.
        """
        # When the agent composes and sends the message, the role of the message is "assistant"
        # unless it's "function".
        valid = self._append_oai_message(message, "assistant", recipient)
        if valid:
            recipient.receive(message, self, request_reply, silent)
        else:
            raise ValueError(
                "Message can't be converted into a valid ChatCompletion message. Either content or function_call must be provided."
            )

    async def a_send(
        self,
        message: Union[Dict, str],
        recipient: Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        """(async) Send a message to another agent.

        Args:
            message (dict or str): message to be sent.
                The message could contain the following fields:
                - content (str or List): Required, the content of the message. (Can be None)
                - function_call (str): the name of the function to be called.
                - name (str): the name of the function to be called.
                - role (str): the role of the message, any role that is not "function"
                    will be modified to "assistant".
                - context (dict): the context of the message, which will be passed to
                    [OpenAIWrapper.create](../oai/client#create).
                    For example, one agent can send a message A as:
        ```python
        {
            "content": lambda context: context["use_tool_msg"],
            "context": {
                "use_tool_msg": "Use tool X if they are relevant."
            }
        }
        ```
                    Next time, one agent can send a message B with a different "use_tool_msg".
                    Then the content of message A will be refreshed to the new "use_tool_msg".
                    So effectively, this provides a way for an agent to send a "link" and modify
                    the content of the "link" later.
            recipient (Agent): the recipient of the message.
            request_reply (bool or None): whether to request a reply from the recipient.
            silent (bool or None): (Experimental) whether to print the message sent.

        Raises:
            ValueError: if the message can't be converted into a valid ChatCompletion message.
        """
        # When the agent composes and sends the message, the role of the message is "assistant"
        # unless it's "function".
        valid = self._append_oai_message(message, "assistant", recipient)
        if valid:
            await recipient.a_receive(message, self, request_reply, silent)
        else:
            raise ValueError(
                "Message can't be converted into a valid ChatCompletion message. Either content or function_call must be provided."
            )

    def _print_received_message(self, message: Union[Dict, str], sender: Agent):
        # print the message received
        print(colored(sender.name, "yellow"), "(to", f"{self.name}):\n", flush=True)
        message = self._message_to_dict(message)

        if message.get("tool_responses"):  # Handle tool multi-call responses
            for tool_response in message["tool_responses"]:
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
                    content = OpenAIWrapper.instantiate(
                        content,
                        message["context"],
                        self.llm_config and self.llm_config.get("allow_format_str_template", False),
                    )
                print(content_str(content), flush=True)
            if "function_call" in message and message["function_call"]:
                function_call = dict(message["function_call"])
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
                    id = tool_call.get("id", "(No id found)")
                    function_call = dict(tool_call.get("function", {}))
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

    def _process_received_message(self, message: Union[Dict, str], sender: Agent, silent: bool):
        # When the agent receives a message, the role of the message is "user". (If 'role' exists and is 'function', it will remain unchanged.)
        valid = self._append_oai_message(message, "user", sender)
        if not valid:
            raise ValueError(
                "Received message can't be converted into a valid ChatCompletion message. Either content or function_call must be provided."
            )
        if not silent:
            self._print_received_message(message, sender)

    def receive(
        self,
        message: Union[Dict, str],
        sender: Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        """Receive a message from another agent.

        Once a message is received, this function sends a reply to the sender or stop.
        The reply can be generated automatically or entered manually by a human.

        Args:
            message (dict or str): message from the sender. If the type is dict, it may contain the following reserved fields (either content or function_call need to be provided).
                1. "content": content of the message, can be None.
                2. "function_call": a dictionary containing the function name and arguments. (deprecated in favor of "tool_calls")
                3. "tool_calls": a list of dictionaries containing the function name and arguments.
                4. "role": role of the message, can be "assistant", "user", "function", "tool".
                    This field is only needed to distinguish between "function" or "assistant"/"user".
                5. "name": In most cases, this field is not needed. When the role is "function", this field is needed to indicate the function name.
                6. "context" (dict): the context of the message, which will be passed to
                    [OpenAIWrapper.create](../oai/client#create).
            sender: sender of an Agent instance.
            request_reply (bool or None): whether a reply is requested from the sender.
                If None, the value is determined by `self.reply_at_receive[sender]`.
            silent (bool or None): (Experimental) whether to print the message received.

        Raises:
            ValueError: if the message can't be converted into a valid ChatCompletion message.
        """
        self._process_received_message(message, sender, silent)
        if request_reply is False or request_reply is None and self.reply_at_receive[sender] is False:
            return
        reply = self.generate_reply(messages=self.chat_messages[sender], sender=sender)
        if reply is not None:
            self.send(reply, sender, silent=silent)

    async def a_receive(
        self,
        message: Union[Dict, str],
        sender: Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        """(async) Receive a message from another agent.

        Once a message is received, this function sends a reply to the sender or stop.
        The reply can be generated automatically or entered manually by a human.

        Args:
            message (dict or str): message from the sender. If the type is dict, it may contain the following reserved fields (either content or function_call need to be provided).
                1. "content": content of the message, can be None.
                2. "function_call": a dictionary containing the function name and arguments. (deprecated in favor of "tool_calls")
                3. "tool_calls": a list of dictionaries containing the function name and arguments.
                4. "role": role of the message, can be "assistant", "user", "function".
                    This field is only needed to distinguish between "function" or "assistant"/"user".
                5. "name": In most cases, this field is not needed. When the role is "function", this field is needed to indicate the function name.
                6. "context" (dict): the context of the message, which will be passed to
                    [OpenAIWrapper.create](../oai/client#create).
            sender: sender of an Agent instance.
            request_reply (bool or None): whether a reply is requested from the sender.
                If None, the value is determined by `self.reply_at_receive[sender]`.
            silent (bool or None): (Experimental) whether to print the message received.

        Raises:
            ValueError: if the message can't be converted into a valid ChatCompletion message.
        """
        self._process_received_message(message, sender, silent)
        if request_reply is False or request_reply is None and self.reply_at_receive[sender] is False:
            return
        reply = await self.a_generate_reply(sender=sender)
        if reply is not None:
            await self.a_send(reply, sender, silent=silent)

    def _prepare_chat(self, recipient: "ConversableAgent", clear_history: bool, prepare_recipient: bool = True) -> None:
        self.reset_consecutive_auto_reply_counter(recipient)
        self.reply_at_receive[recipient] = True
        if clear_history:
            self.clear_history(recipient)
        if prepare_recipient:
            recipient._prepare_chat(self, clear_history, False)

    def _raise_exception_on_async_reply_functions(self) -> None:
        """Raise an exception if any async reply functions are registered.

        Raises:
            RuntimeError: if any async reply functions are registered.
        """
        reply_functions = {f["reply_func"] for f in self._reply_func_list}.difference(
            self._ignore_async_func_in_sync_chat_list
        )

        async_reply_functions = [f for f in reply_functions if inspect.iscoroutinefunction(f)]
        if async_reply_functions != []:
            msg = (
                "Async reply functions can only be used with ConversableAgent.a_initiate_chat(). The following async reply functions are found: "
                + ", ".join([f.__name__ for f in async_reply_functions])
            )

            raise RuntimeError(msg)

    def initiate_chat(
        self,
        recipient: "ConversableAgent",
        clear_history: Optional[bool] = True,
        silent: Optional[bool] = False,
        cache: Optional[Cache] = None,
        **context,
    ):
        """Initiate a chat with the recipient agent.

        Reset the consecutive auto reply counter.
        If `clear_history` is True, the chat history with the recipient agent will be cleared.
        `generate_init_message` is called to generate the initial message for the agent.

        Args:
            recipient: the recipient agent.
            clear_history (bool): whether to clear the chat history with the agent.
            silent (bool or None): (Experimental) whether to print the messages for this conversation.
            cache (Cache or None): the cache client to be used for this conversation.
            **context: any context information.
                "message" needs to be provided if the `generate_init_message` method is not overridden.
                          Otherwise, input() will be called to get the initial message.

        Raises:
            RuntimeError: if any async reply functions are registered and not ignored in sync chat.
        """
        for agent in [self, recipient]:
            agent._raise_exception_on_async_reply_functions()
            agent.previous_cache = agent.client_cache
            agent.client_cache = cache
        self._prepare_chat(recipient, clear_history)
        self.send(self.generate_init_message(**context), recipient, silent=silent)
        for agent in [self, recipient]:
            agent.client_cache = agent.previous_cache
            agent.previous_cache = None

    async def a_initiate_chat(
        self,
        recipient: "ConversableAgent",
        clear_history: Optional[bool] = True,
        silent: Optional[bool] = False,
        cache: Optional[Cache] = None,
        **context,
    ):
        """(async) Initiate a chat with the recipient agent.

        Reset the consecutive auto reply counter.
        If `clear_history` is True, the chat history with the recipient agent will be cleared.
        `generate_init_message` is called to generate the initial message for the agent.

        Args:
            recipient: the recipient agent.
            clear_history (bool): whether to clear the chat history with the agent.
            silent (bool or None): (Experimental) whether to print the messages for this conversation.
            cache (Cache or None): the cache client to be used for this conversation.
            **context: any context information.
                "message" needs to be provided if the `generate_init_message` method is not overridden.
                          Otherwise, input() will be called to get the initial message.
        """
        self._prepare_chat(recipient, clear_history)
        for agent in [self, recipient]:
            agent.previous_cache = agent.client_cache
            agent.client_cache = cache
        await self.a_send(await self.a_generate_init_message(**context), recipient, silent=silent)
        for agent in [self, recipient]:
            agent.client_cache = agent.previous_cache
            agent.previous_cache = None

    def reset(self):
        """Reset the agent."""
        self.clear_history()
        self.reset_consecutive_auto_reply_counter()
        self.stop_reply_at_receive()
        if self.client is not None:
            self.client.clear_usage_summary()
        for reply_func_tuple in self._reply_func_list:
            if reply_func_tuple["reset_config"] is not None:
                reply_func_tuple["reset_config"](reply_func_tuple["config"])
            else:
                reply_func_tuple["config"] = copy.copy(reply_func_tuple["init_config"])

    def stop_reply_at_receive(self, sender: Optional[Agent] = None):
        """Reset the reply_at_receive of the sender."""
        if sender is None:
            self.reply_at_receive.clear()
        else:
            self.reply_at_receive[sender] = False

    def reset_consecutive_auto_reply_counter(self, sender: Optional[Agent] = None):
        """Reset the consecutive_auto_reply_counter of the sender."""
        if sender is None:
            self._consecutive_auto_reply_counter.clear()
        else:
            self._consecutive_auto_reply_counter[sender] = 0

    def clear_history(self, agent: Optional[Agent] = None):
        """Clear the chat history of the agent.

        Args:
            agent: the agent with whom the chat history to clear. If None, clear the chat history with all agents.
        """
        if agent is None:
            self._oai_messages.clear()
        else:
            self._oai_messages[agent].clear()

    def generate_oai_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate a reply using autogen.oai."""
        client = self.client if config is None else config
        if client is None:
            return False, None
        if messages is None:
            messages = self._oai_messages[sender]

        # unroll tool_responses
        all_messages = []
        for message in messages:
            tool_responses = message.get("tool_responses", [])
            if tool_responses:
                all_messages += tool_responses
                # tool role on the parent message means the content is just concatenation of all of the tool_responses
                if message.get("role") != "tool":
                    all_messages.append({key: message[key] for key in message if key != "tool_responses"})
            else:
                all_messages.append(message)

        # TODO: #1143 handle token limit exceeded error
        response = client.create(
            context=messages[-1].pop("context", None),
            messages=self._oai_system_message + all_messages,
            cache=self.client_cache,
        )

        extracted_response = client.extract_text_or_completion_object(response)[0]

        # ensure function and tool calls will be accepted when sent back to the LLM
        if not isinstance(extracted_response, str):
            extracted_response = model_dump(extracted_response)
        if isinstance(extracted_response, dict):
            if extracted_response.get("function_call"):
                extracted_response["function_call"]["name"] = self._normalize_name(
                    extracted_response["function_call"]["name"]
                )
            for tool_call in extracted_response.get("tool_calls") or []:
                tool_call["function"]["name"] = self._normalize_name(tool_call["function"]["name"])
        return True, extracted_response

    async def a_generate_oai_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate a reply using autogen.oai asynchronously."""
        return await asyncio.get_event_loop().run_in_executor(
            None, functools.partial(self.generate_oai_reply, messages=messages, sender=sender, config=config)
        )

    def generate_code_execution_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Union[Dict, Literal[False]]] = None,
    ):
        """Generate a reply using code execution."""
        code_execution_config = config if config is not None else self._code_execution_config
        if code_execution_config is False:
            return False, None
        if messages is None:
            messages = self._oai_messages[sender]
        last_n_messages = code_execution_config.pop("last_n_messages", "auto")

        if not (isinstance(last_n_messages, (int, float)) and last_n_messages >= 0) and last_n_messages != "auto":
            raise ValueError("last_n_messages must be either a non-negative integer, or the string 'auto'.")

        messages_to_scan = last_n_messages
        if last_n_messages == "auto":
            # Find when the agent last spoke
            messages_to_scan = 0
            for i in range(len(messages)):
                message = messages[-(i + 1)]
                if "role" not in message:
                    break
                elif message["role"] != "user":
                    break
                else:
                    messages_to_scan += 1

        # iterate through the last n messages in reverse
        # if code blocks are found, execute the code blocks and return the output
        # if no code blocks are found, continue
        for i in range(min(len(messages), messages_to_scan)):
            message = messages[-(i + 1)]
            if not message["content"]:
                continue
            code_blocks = extract_code(message["content"])
            if len(code_blocks) == 1 and code_blocks[0][0] == UNKNOWN:
                continue

            # found code blocks, execute code and push "last_n_messages" back
            exitcode, logs = self.execute_code_blocks(code_blocks)
            code_execution_config["last_n_messages"] = last_n_messages
            exitcode2str = "execution succeeded" if exitcode == 0 else "execution failed"
            return True, f"exitcode: {exitcode} ({exitcode2str})\nCode output: {logs}"

        # no code blocks are found, push last_n_messages back and return.
        code_execution_config["last_n_messages"] = last_n_messages

        return False, None

    def generate_function_call_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[Dict, None]]:
        """
        Generate a reply using function call.

        "function_call" replaced by "tool_calls" as of [OpenAI API v1.1.0](https://github.com/openai/openai-python/releases/tag/v1.1.0)
        See https://platform.openai.com/docs/api-reference/chat/create#chat-create-functions
        """
        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        if "function_call" in message and message["function_call"]:
            func_call = message["function_call"]
            func = self._function_map.get(func_call.get("name", None), None)
            if inspect.iscoroutinefunction(func):
                return False, None

            _, func_return = self.execute_function(message["function_call"])
            return True, func_return
        return False, None

    async def a_generate_function_call_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[Dict, None]]:
        """
        Generate a reply using async function call.

        "function_call" replaced by "tool_calls" as of [OpenAI API v1.1.0](https://github.com/openai/openai-python/releases/tag/v1.1.0)
        See https://platform.openai.com/docs/api-reference/chat/create#chat-create-functions
        """
        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        if "function_call" in message:
            func_call = message["function_call"]
            func_name = func_call.get("name", "")
            func = self._function_map.get(func_name, None)
            if func and inspect.iscoroutinefunction(func):
                _, func_return = await self.a_execute_function(func_call)
                return True, func_return

        return False, None

    def _str_for_tool_response(self, tool_response):
        func_id = tool_response.get("tool_call_id", "")
        response = tool_response.get("content", "")
        return f"Tool Call Id: {func_id}\n{response}"

    def generate_tool_calls_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[Dict, None]]:
        """Generate a reply using tool call."""
        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        tool_returns = []
        for tool_call in message.get("tool_calls", []):
            id = tool_call["id"]
            function_call = tool_call.get("function", {})
            func = self._function_map.get(function_call.get("name", None), None)
            if inspect.iscoroutinefunction(func):
                continue
            _, func_return = self.execute_function(function_call)
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

    async def _a_execute_tool_call(self, tool_call):
        id = tool_call["id"]
        function_call = tool_call.get("function", {})
        _, func_return = await self.a_execute_function(function_call)
        return {
            "tool_call_id": id,
            "role": "tool",
            "content": func_return.get("content", ""),
        }

    async def a_generate_tool_calls_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[Dict, None]]:
        """Generate a reply using async function call."""
        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
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

    def check_termination_and_human_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, None]]:
        """Check if the conversation should be terminated, and if human reply is provided.

        This method checks for conditions that require the conversation to be terminated, such as reaching
        a maximum number of consecutive auto-replies or encountering a termination message. Additionally,
        it prompts for and processes human input based on the configured human input mode, which can be
        'ALWAYS', 'NEVER', or 'TERMINATE'. The method also manages the consecutive auto-reply counter
        for the conversation and prints relevant messages based on the human input received.

        Args:
            - messages (Optional[List[Dict]]): A list of message dictionaries, representing the conversation history.
            - sender (Optional[Agent]): The agent object representing the sender of the message.
            - config (Optional[Any]): Configuration object, defaults to the current instance if not provided.

        Returns:
            - Tuple[bool, Union[str, Dict, None]]: A tuple containing a boolean indicating if the conversation
            should be terminated, and a human reply which can be a string, a dictionary, or None.
        """
        # Function implementation...

        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        reply = ""
        no_human_input_msg = ""
        if self.human_input_mode == "ALWAYS":
            reply = self.get_human_input(
                f"Provide feedback to {sender.name}. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "
            )
            no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
            # if the human input is empty, and the message is a termination message, then we will terminate the conversation
            reply = reply if reply or not self._is_termination_msg(message) else "exit"
        else:
            if self._consecutive_auto_reply_counter[sender] >= self._max_consecutive_auto_reply_dict[sender]:
                if self.human_input_mode == "NEVER":
                    reply = "exit"
                else:
                    # self.human_input_mode == "TERMINATE":
                    terminate = self._is_termination_msg(message)
                    reply = self.get_human_input(
                        f"Please give feedback to {sender.name}. Press enter or type 'exit' to stop the conversation: "
                        if terminate
                        else f"Please give feedback to {sender.name}. Press enter to skip and use auto-reply, or type 'exit' to stop the conversation: "
                    )
                    no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
                    # if the human input is empty, and the message is a termination message, then we will terminate the conversation
                    reply = reply if reply or not terminate else "exit"
            elif self._is_termination_msg(message):
                if self.human_input_mode == "NEVER":
                    reply = "exit"
                else:
                    # self.human_input_mode == "TERMINATE":
                    reply = self.get_human_input(
                        f"Please give feedback to {sender.name}. Press enter or type 'exit' to stop the conversation: "
                    )
                    no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
                    # if the human input is empty, and the message is a termination message, then we will terminate the conversation
                    reply = reply or "exit"

        # print the no_human_input_msg
        if no_human_input_msg:
            print(colored(f"\n>>>>>>>> {no_human_input_msg}", "red"), flush=True)

        # stop the conversation
        if reply == "exit":
            # reset the consecutive_auto_reply_counter
            self._consecutive_auto_reply_counter[sender] = 0
            return True, None

        # send the human reply
        if reply or self._max_consecutive_auto_reply_dict[sender] == 0:
            # reset the consecutive_auto_reply_counter
            self._consecutive_auto_reply_counter[sender] = 0
            # User provided a custom response, return function and tool failures indicating user interruption
            tool_returns = []
            if message.get("function_call", False):
                tool_returns.append(
                    {
                        "role": "function",
                        "name": message["function_call"].get("name", ""),
                        "content": "USER INTERRUPTED",
                    }
                )

            if message.get("tool_calls", False):
                tool_returns.extend(
                    [
                        {"role": "tool", "tool_call_id": tool_call.get("id", ""), "content": "USER INTERRUPTED"}
                        for tool_call in message["tool_calls"]
                    ]
                )

            response = {"role": "user", "content": reply}
            if tool_returns:
                response["tool_responses"] = tool_returns

            return True, response

        # increment the consecutive_auto_reply_counter
        self._consecutive_auto_reply_counter[sender] += 1
        if self.human_input_mode != "NEVER":
            print(colored("\n>>>>>>>> USING AUTO REPLY...", "red"), flush=True)

        return False, None

    async def a_check_termination_and_human_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, None]]:
        """(async) Check if the conversation should be terminated, and if human reply is provided.

        This method checks for conditions that require the conversation to be terminated, such as reaching
        a maximum number of consecutive auto-replies or encountering a termination message. Additionally,
        it prompts for and processes human input based on the configured human input mode, which can be
        'ALWAYS', 'NEVER', or 'TERMINATE'. The method also manages the consecutive auto-reply counter
        for the conversation and prints relevant messages based on the human input received.

        Args:
            - messages (Optional[List[Dict]]): A list of message dictionaries, representing the conversation history.
            - sender (Optional[Agent]): The agent object representing the sender of the message.
            - config (Optional[Any]): Configuration object, defaults to the current instance if not provided.

        Returns:
            - Tuple[bool, Union[str, Dict, None]]: A tuple containing a boolean indicating if the conversation
            should be terminated, and a human reply which can be a string, a dictionary, or None.
        """
        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        reply = ""
        no_human_input_msg = ""
        if self.human_input_mode == "ALWAYS":
            reply = await self.a_get_human_input(
                f"Provide feedback to {sender.name}. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "
            )
            no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
            # if the human input is empty, and the message is a termination message, then we will terminate the conversation
            reply = reply if reply or not self._is_termination_msg(message) else "exit"
        else:
            if self._consecutive_auto_reply_counter[sender] >= self._max_consecutive_auto_reply_dict[sender]:
                if self.human_input_mode == "NEVER":
                    reply = "exit"
                else:
                    # self.human_input_mode == "TERMINATE":
                    terminate = self._is_termination_msg(message)
                    reply = await self.a_get_human_input(
                        f"Please give feedback to {sender.name}. Press enter or type 'exit' to stop the conversation: "
                        if terminate
                        else f"Please give feedback to {sender.name}. Press enter to skip and use auto-reply, or type 'exit' to stop the conversation: "
                    )
                    no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
                    # if the human input is empty, and the message is a termination message, then we will terminate the conversation
                    reply = reply if reply or not terminate else "exit"
            elif self._is_termination_msg(message):
                if self.human_input_mode == "NEVER":
                    reply = "exit"
                else:
                    # self.human_input_mode == "TERMINATE":
                    reply = await self.a_get_human_input(
                        f"Please give feedback to {sender.name}. Press enter or type 'exit' to stop the conversation: "
                    )
                    no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
                    # if the human input is empty, and the message is a termination message, then we will terminate the conversation
                    reply = reply or "exit"

        # print the no_human_input_msg
        if no_human_input_msg:
            print(colored(f"\n>>>>>>>> {no_human_input_msg}", "red"), flush=True)

        # stop the conversation
        if reply == "exit":
            # reset the consecutive_auto_reply_counter
            self._consecutive_auto_reply_counter[sender] = 0
            return True, None

        # send the human reply
        if reply or self._max_consecutive_auto_reply_dict[sender] == 0:
            # User provided a custom response, return function and tool results indicating user interruption
            # reset the consecutive_auto_reply_counter
            self._consecutive_auto_reply_counter[sender] = 0
            tool_returns = []
            if message.get("function_call", False):
                tool_returns.append(
                    {
                        "role": "function",
                        "name": message["function_call"].get("name", ""),
                        "content": "USER INTERRUPTED",
                    }
                )

            if message.get("tool_calls", False):
                tool_returns.extend(
                    [
                        {"role": "tool", "tool_call_id": tool_call.get("id", ""), "content": "USER INTERRUPTED"}
                        for tool_call in message["tool_calls"]
                    ]
                )

            response = {"role": "user", "content": reply}
            if tool_returns:
                response["tool_responses"] = tool_returns

            return True, response

        # increment the consecutive_auto_reply_counter
        self._consecutive_auto_reply_counter[sender] += 1
        if self.human_input_mode != "NEVER":
            print(colored("\n>>>>>>>> USING AUTO REPLY...", "red"), flush=True)

        return False, None

    def generate_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        exclude: Optional[List[Callable]] = None,
    ) -> Union[str, Dict, None]:
        """Reply based on the conversation history and the sender.

        Either messages or sender must be provided.
        Register a reply_func with `None` as one trigger for it to be activated when `messages` is non-empty and `sender` is `None`.
        Use registered auto reply functions to generate replies.
        By default, the following functions are checked in order:
        1. check_termination_and_human_reply
        2. generate_function_call_reply (deprecated in favor of tool_calls)
        3. generate_tool_calls_reply
        4. generate_code_execution_reply
        5. generate_oai_reply
        Every function returns a tuple (final, reply).
        When a function returns final=False, the next function will be checked.
        So by default, termination and human reply will be checked first.
        If not terminating and human reply is skipped, execute function or code and return the result.
        AI replies are generated only when no code execution is performed.

        Args:
            messages: a list of messages in the conversation history.
            default_reply (str or dict): default reply.
            sender: sender of an Agent instance.
            exclude: a list of functions to exclude.

        Returns:
            str or dict or None: reply. None if no reply is generated.
        """
        if all((messages is None, sender is None)):
            error_msg = f"Either {messages=} or {sender=} must be provided."
            logger.error(error_msg)
            raise AssertionError(error_msg)

        if messages is None:
            messages = self._oai_messages[sender]

        # Call the hookable method that gives registered hooks a chance to process the last message.
        # Message modifications do not affect the incoming messages or self._oai_messages.
        messages = self.process_last_message(messages)

        for reply_func_tuple in self._reply_func_list:
            reply_func = reply_func_tuple["reply_func"]
            if exclude and reply_func in exclude:
                continue
            if inspect.iscoroutinefunction(reply_func):
                continue
            if self._match_trigger(reply_func_tuple["trigger"], sender):
                final, reply = reply_func(self, messages=messages, sender=sender, config=reply_func_tuple["config"])
                if final:
                    return reply
        return self._default_auto_reply

    async def a_generate_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        exclude: Optional[List[Callable]] = None,
    ) -> Union[str, Dict, None]:
        """(async) Reply based on the conversation history and the sender.

        Either messages or sender must be provided.
        Register a reply_func with `None` as one trigger for it to be activated when `messages` is non-empty and `sender` is `None`.
        Use registered auto reply functions to generate replies.
        By default, the following functions are checked in order:
        1. check_termination_and_human_reply
        2. generate_function_call_reply
        3. generate_tool_calls_reply
        4. generate_code_execution_reply
        5. generate_oai_reply
        Every function returns a tuple (final, reply).
        When a function returns final=False, the next function will be checked.
        So by default, termination and human reply will be checked first.
        If not terminating and human reply is skipped, execute function or code and return the result.
        AI replies are generated only when no code execution is performed.

        Args:
            messages: a list of messages in the conversation history.
            default_reply (str or dict): default reply.
            sender: sender of an Agent instance.
            exclude: a list of functions to exclude.

        Returns:
            str or dict or None: reply. None if no reply is generated.
        """
        if all((messages is None, sender is None)):
            error_msg = f"Either {messages=} or {sender=} must be provided."
            logger.error(error_msg)
            raise AssertionError(error_msg)

        if messages is None:
            messages = self._oai_messages[sender]

        # Call the hookable method that gives registered hooks a chance to process the last message.
        # Message modifications do not affect the incoming messages or self._oai_messages.
        messages = self.process_last_message(messages)

        for reply_func_tuple in self._reply_func_list:
            reply_func = reply_func_tuple["reply_func"]
            if exclude and reply_func in exclude:
                continue
            if self._match_trigger(reply_func_tuple["trigger"], sender):
                if inspect.iscoroutinefunction(reply_func):
                    final, reply = await reply_func(
                        self, messages=messages, sender=sender, config=reply_func_tuple["config"]
                    )
                else:
                    final, reply = reply_func(self, messages=messages, sender=sender, config=reply_func_tuple["config"])
                if final:
                    return reply
        return self._default_auto_reply

    def _match_trigger(self, trigger: Union[None, str, type, Agent, Callable, List], sender: Agent) -> bool:
        """Check if the sender matches the trigger.

        Args:
            - trigger (Union[None, str, type, Agent, Callable, List]): The condition to match against the sender.
            Can be `None`, string, type, `Agent` instance, callable, or a list of these.
            - sender (Agent): The sender object or type to be matched against the trigger.

        Returns:
            - bool: Returns `True` if the sender matches the trigger, otherwise `False`.

        Raises:
            - ValueError: If the trigger type is unsupported.
        """
        if trigger is None:
            return sender is None
        elif isinstance(trigger, str):
            return trigger == sender.name
        elif isinstance(trigger, type):
            return isinstance(sender, trigger)
        elif isinstance(trigger, Agent):
            # return True if the sender is the same type (class) as the trigger
            return trigger == sender
        elif isinstance(trigger, Callable):
            rst = trigger(sender)
            assert rst in [True, False], f"trigger {trigger} must return a boolean value."
            return rst
        elif isinstance(trigger, list):
            return any(self._match_trigger(t, sender) for t in trigger)
        else:
            raise ValueError(f"Unsupported trigger type: {type(trigger)}")

    def get_human_input(self, prompt: str) -> str:
        """Get human input.

        Override this method to customize the way to get human input.

        Args:
            prompt (str): prompt for the human input.

        Returns:
            str: human input.
        """
        reply = input(prompt)
        return reply

    async def a_get_human_input(self, prompt: str) -> str:
        """(Async) Get human input.

        Override this method to customize the way to get human input.

        Args:
            prompt (str): prompt for the human input.

        Returns:
            str: human input.
        """
        reply = input(prompt)
        return reply

    def run_code(self, code, **kwargs):
        """Run the code and return the result.

        Override this function to modify the way to run the code.
        Args:
            code (str): the code to be executed.
            **kwargs: other keyword arguments.

        Returns:
            A tuple of (exitcode, logs, image).
            exitcode (int): the exit code of the code execution.
            logs (str): the logs of the code execution.
            image (str or None): the docker image used for the code execution.
        """
        return execute_code(code, **kwargs)

    def execute_code_blocks(self, code_blocks):
        """Execute the code blocks and return the result."""
        logs_all = ""
        for i, code_block in enumerate(code_blocks):
            lang, code = code_block
            if not lang:
                lang = infer_lang(code)
            print(
                colored(
                    f"\n>>>>>>>> EXECUTING CODE BLOCK {i} (inferred language is {lang})...",
                    "red",
                ),
                flush=True,
            )
            if lang in ["bash", "shell", "sh"]:
                exitcode, logs, image = self.run_code(code, lang=lang, **self._code_execution_config)
            elif lang in ["python", "Python"]:
                if code.startswith("# filename: "):
                    filename = code[11 : code.find("\n")].strip()
                else:
                    filename = None
                exitcode, logs, image = self.run_code(
                    code,
                    lang="python",
                    filename=filename,
                    **self._code_execution_config,
                )
            else:
                # In case the language is not supported, we return an error message.
                exitcode, logs, image = (
                    1,
                    f"unknown language {lang}",
                    None,
                )
                # raise NotImplementedError
            if image is not None:
                self._code_execution_config["use_docker"] = image
            logs_all += "\n" + logs
            if exitcode != 0:
                return exitcode, logs_all
        return exitcode, logs_all

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

    def execute_function(self, func_call, verbose: bool = False) -> Tuple[bool, Dict[str, str]]:
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

    async def a_execute_function(self, func_call):
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

    def generate_init_message(self, **context) -> Union[str, Dict]:
        """Generate the initial message for the agent.

        Override this function to customize the initial message based on user's request.
        If not overridden, "message" needs to be provided in the context.

        Args:
            **context: any context information, and "message" parameter needs to be provided.
                       If message is not given, prompt for it via input()
        """
        if "message" not in context:
            context["message"] = self.get_human_input(">")
        return context["message"]

    async def a_generate_init_message(self, **context) -> Union[str, Dict]:
        """Generate the initial message for the agent.

        Override this function to customize the initial message based on user's request.
        If not overridden, "message" needs to be provided in the context.

        Args:
            **context: any context information, and "message" parameter needs to be provided.
                       If message is not given, prompt for it via input()
        """
        if "message" not in context:
            context["message"] = await self.a_get_human_input(">")
        return context["message"]

    def register_function(self, function_map: Dict[str, Callable]):
        """Register functions to the agent.

        Args:
            function_map: a dictionary mapping function names to functions.
        """
        for name in function_map.keys():
            self._assert_valid_name(name)
        self._function_map.update(function_map)

    def update_function_signature(self, func_sig: Union[str, Dict], is_remove: None):
        """update a function_signature in the LLM configuration for function_call.

        Args:
            func_sig (str or dict): description/name of the function to update/remove to the model. See: https://platform.openai.com/docs/api-reference/chat/create#chat/create-functions
            is_remove: whether removing the function from llm_config with name 'func_sig'

        Deprecated as of [OpenAI API v1.1.0](https://github.com/openai/openai-python/releases/tag/v1.1.0)
        See https://platform.openai.com/docs/api-reference/chat/create#chat-create-function_call
        """

        if not isinstance(self.llm_config, dict):
            error_msg = "To update a function signature, agent must have an llm_config"
            logger.error(error_msg)
            raise AssertionError(error_msg)

        if is_remove:
            if "functions" not in self.llm_config.keys():
                error_msg = "The agent config doesn't have function {name}.".format(name=func_sig)
                logger.error(error_msg)
                raise AssertionError(error_msg)
            else:
                self.llm_config["functions"] = [
                    func for func in self.llm_config["functions"] if func["name"] != func_sig
                ]
        else:
            self._assert_valid_name(func_sig["name"])
            if "functions" in self.llm_config.keys():
                self.llm_config["functions"] = [
                    func for func in self.llm_config["functions"] if func.get("name") != func_sig["name"]
                ] + [func_sig]
            else:
                self.llm_config["functions"] = [func_sig]

        if len(self.llm_config["functions"]) == 0:
            del self.llm_config["functions"]

        self.client = OpenAIWrapper(**self.llm_config)

    def update_tool_signature(self, tool_sig: Union[str, Dict], is_remove: None):
        """update a tool_signature in the LLM configuration for tool_call.

        Args:
            tool_sig (str or dict): description/name of the tool to update/remove to the model. See: https://platform.openai.com/docs/api-reference/chat/create#chat-create-tools
            is_remove: whether removing the tool from llm_config with name 'tool_sig'
        """

        if not self.llm_config:
            error_msg = "To update a tool signature, agent must have an llm_config"
            logger.error(error_msg)
            raise AssertionError(error_msg)

        if is_remove:
            if "tools" not in self.llm_config.keys():
                error_msg = "The agent config doesn't have tool {name}.".format(name=tool_sig)
                logger.error(error_msg)
                raise AssertionError(error_msg)
            else:
                self.llm_config["tools"] = [
                    tool for tool in self.llm_config["tools"] if tool["function"]["name"] != tool_sig
                ]
        else:
            self._assert_valid_name(tool_sig["function"]["name"])
            if "tools" in self.llm_config.keys():
                self.llm_config["tools"] = [
                    tool
                    for tool in self.llm_config["tools"]
                    if tool.get("function", {}).get("name") != tool_sig["function"]["name"]
                ] + [tool_sig]
            else:
                self.llm_config["tools"] = [tool_sig]

        if len(self.llm_config["tools"]) == 0:
            del self.llm_config["tools"]

        self.client = OpenAIWrapper(**self.llm_config)

    def can_execute_function(self, name: Union[List[str], str]) -> bool:
        """Whether the agent can execute the function."""
        names = name if isinstance(name, list) else [name]
        return all([n in self._function_map for n in names])

    @property
    def function_map(self) -> Dict[str, Callable]:
        """Return the function map."""
        return self._function_map

    def _wrap_function(self, func: F) -> F:
        """Wrap the function to dump the return value to json.

        Handles both sync and async functions.

        Args:
            func: the function to be wrapped.

        Returns:
            The wrapped function.
        """

        @load_basemodels_if_needed
        @functools.wraps(func)
        def _wrapped_func(*args, **kwargs):
            retval = func(*args, **kwargs)

            return serialize_to_str(retval)

        @load_basemodels_if_needed
        @functools.wraps(func)
        async def _a_wrapped_func(*args, **kwargs):
            retval = await func(*args, **kwargs)
            return serialize_to_str(retval)

        wrapped_func = _a_wrapped_func if inspect.iscoroutinefunction(func) else _wrapped_func

        # needed for testing
        wrapped_func._origin = func

        return wrapped_func

    def register_for_llm(
        self,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        api_style: Literal["function", "tool"] = "tool",
    ) -> Callable[[F], F]:
        """Decorator factory for registering a function to be used by an agent.

        It's return value is used to decorate a function to be registered to the agent. The function uses type hints to
        specify the arguments and return type. The function name is used as the default name for the function,
        but a custom name can be provided. The function description is used to describe the function in the
        agent's configuration.

        Args:
            name (optional(str)): name of the function. If None, the function name will be used (default: None).
            description (optional(str)): description of the function (default: None). It is mandatory
                for the initial decorator, but the following ones can omit it.
            api_style: (literal): the API style for function call.
                For Azure OpenAI API, use version 2023-12-01-preview or later.
                `"function"` style will be deprecated. For earlier version use
                `"function"` if `"tool"` doesn't work.
                See [Azure OpenAI documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/function-calling?tabs=python) for details.

        Returns:
            The decorator for registering a function to be used by an agent.

        Examples:
            ```
            @user_proxy.register_for_execution()
            @agent2.register_for_llm()
            @agent1.register_for_llm(description="This is a very useful function")
            def my_function(a: Annotated[str, "description of a parameter"] = "a", b: int, c=3.14) -> str:
                 return a + str(b * c)
            ```

            For Azure OpenAI versions prior to 2023-12-01-preview, set `api_style`
            to `"function"` if `"tool"` doesn't work:
            ```
            @agent2.register_for_llm(api_style="function")
            def my_function(a: Annotated[str, "description of a parameter"] = "a", b: int, c=3.14) -> str:
                 return a + str(b * c)
            ```

        """

        def _decorator(func: F) -> F:
            """Decorator for registering a function to be used by an agent.

            Args:
                func: the function to be registered.

            Returns:
                The function to be registered, with the _description attribute set to the function description.

            Raises:
                ValueError: if the function description is not provided and not propagated by a previous decorator.
                RuntimeError: if the LLM config is not set up before registering a function.

            """
            # name can be overwritten by the parameter, by default it is the same as function name
            if name:
                func._name = name
            elif not hasattr(func, "_name"):
                func._name = func.__name__

            # description is propagated from the previous decorator, but it is mandatory for the first one
            if description:
                func._description = description
            else:
                if not hasattr(func, "_description"):
                    raise ValueError("Function description is required, none found.")

            # get JSON schema for the function
            f = get_function_schema(func, name=func._name, description=func._description)

            # register the function to the agent if there is LLM config, raise an exception otherwise
            if self.llm_config is None:
                raise RuntimeError("LLM config must be setup before registering a function for LLM.")

            if api_style == "function":
                f = f["function"]
                self.update_function_signature(f, is_remove=False)
            elif api_style == "tool":
                self.update_tool_signature(f, is_remove=False)
            else:
                raise ValueError(f"Unsupported API style: {api_style}")

            return func

        return _decorator

    def register_for_execution(
        self,
        name: Optional[str] = None,
    ) -> Callable[[F], F]:
        """Decorator factory for registering a function to be executed by an agent.

        It's return value is used to decorate a function to be registered to the agent.

        Args:
            name (optional(str)): name of the function. If None, the function name will be used (default: None).

        Returns:
            The decorator for registering a function to be used by an agent.

        Examples:
            ```
            @user_proxy.register_for_execution()
            @agent2.register_for_llm()
            @agent1.register_for_llm(description="This is a very useful function")
            def my_function(a: Annotated[str, "description of a parameter"] = "a", b: int, c=3.14):
                 return a + str(b * c)
            ```

        """

        def _decorator(func: F) -> F:
            """Decorator for registering a function to be used by an agent.

            Args:
                func: the function to be registered.

            Returns:
                The function to be registered, with the _description attribute set to the function description.

            Raises:
                ValueError: if the function description is not provided and not propagated by a previous decorator.

            """
            # name can be overwritten by the parameter, by default it is the same as function name
            if name:
                func._name = name
            elif not hasattr(func, "_name"):
                func._name = func.__name__

            self.register_function({func._name: self._wrap_function(func)})

            return func

        return _decorator

    def register_hook(self, hookable_method: Callable, hook: Callable):
        """
        Registers a hook to be called by a hookable method, in order to add a capability to the agent.
        Registered hooks are kept in lists (one per hookable method), and are called in their order of registration.

        Args:
            hookable_method: A hookable method implemented by ConversableAgent.
            hook: A method implemented by a subclass of AgentCapability.
        """
        assert hookable_method in self.hook_lists, f"{hookable_method} is not a hookable method."
        hook_list = self.hook_lists[hookable_method]
        assert hook not in hook_list, f"{hook} is already registered as a hook."
        hook_list.append(hook)

    def process_last_message(self, messages):
        """
        Calls any registered capability hooks to use and potentially modify the text of the last message,
        as long as the last message is not a function call or exit command.
        """

        # If any required condition is not met, return the original message list.
        hook_list = self.hook_lists[self.process_last_message]
        if len(hook_list) == 0:
            return messages  # No hooks registered.
        if messages is None:
            return None  # No message to process.
        if len(messages) == 0:
            return messages  # No message to process.
        last_message = messages[-1]
        if "function_call" in last_message:
            return messages  # Last message is a function call.
        if "context" in last_message:
            return messages  # Last message contains a context key.
        if "content" not in last_message:
            return messages  # Last message has no content.
        user_text = last_message["content"]
        if not isinstance(user_text, str):
            return messages  # Last message content is not a string. TODO: Multimodal agents will use a dict here.
        if user_text == "exit":
            return messages  # Last message is an exit command.

        # Call each hook (in order of registration) to process the user's message.
        processed_user_text = user_text
        for hook in hook_list:
            processed_user_text = hook(processed_user_text)
        if processed_user_text == user_text:
            return messages  # No hooks actually modified the user's message.

        # Replace the last user message with the expanded one.
        messages = messages.copy()
        messages[-1]["content"] = processed_user_text
        return messages

    def print_usage_summary(self, mode: Union[str, List[str]] = ["actual", "total"]) -> None:
        """Print the usage summary."""
        if self.client is None:
            print(f"No cost incurred from agent '{self.name}'.")
        else:
            print(f"Agent '{self.name}':")
            self.client.print_usage_summary(mode)

    def get_actual_usage(self) -> Union[None, Dict[str, int]]:
        """Get the actual usage summary."""
        if self.client is None:
            return None
        else:
            return self.client.actual_usage_summary

    def get_total_usage(self) -> Union[None, Dict[str, int]]:
        """Get the total usage summary."""
        if self.client is None:
            return None
        else:
            return self.client.total_usage_summary
