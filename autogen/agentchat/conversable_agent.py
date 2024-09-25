import asyncio
import copy
import functools
import inspect
import json
import logging
import re
import warnings
from collections import defaultdict
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union

from openai import BadRequestError

from autogen.agentchat.chat import _post_process_carryover_item
from autogen.exception_utils import InvalidCarryOverType, SenderRequired

from .._pydantic import model_dump
from ..cache.cache import AbstractCache
from ..code_utils import (
    PYTHON_VARIANTS,
    UNKNOWN,
    check_can_use_docker_or_throw,
    content_str,
    decide_use_docker,
    execute_code,
    extract_code,
    infer_lang,
)
from ..coding.base import CodeExecutor
from ..coding.factory import CodeExecutorFactory
from ..formatting_utils import colored
from ..function_utils import get_function_schema, load_basemodels_if_needed, serialize_to_str
from ..io.base import IOStream
from ..oai.client import ModelClient, OpenAIWrapper
from ..runtime_logging import log_event, log_function_use, log_new_agent, logging_enabled
from .agent import Agent, LLMAgent
from .chat import ChatResult, a_initiate_chats, initiate_chats
from .utils import consolidate_chat_info, gather_usage_summary

__all__ = ("ConversableAgent",)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class ConversableAgent(LLMAgent):
    """(In preview) A class for generic conversable agents which can be configured as assistant or user proxy.

    After receiving each message, the agent will send a reply to the sender unless the msg is a termination msg.
    For example, AssistantAgent and UserProxyAgent are subclasses of this class,
    configured with different default settings.

    To modify auto reply, override `generate_reply` method.
    To disable/enable human response in every turn, set `human_input_mode` to "NEVER" or "ALWAYS".
    To modify the way to get human input, override `get_human_input` method.
    To modify the way to execute code blocks, single code block, or function call, override `execute_code_blocks`,
    `run_code`, and `execute_function` methods respectively.
    """

    DEFAULT_CONFIG = False  # False or dict, the default config for llm inference
    MAX_CONSECUTIVE_AUTO_REPLY = 100  # maximum number of consecutive auto replies (subject to future change)

    DEFAULT_SUMMARY_PROMPT = "Summarize the takeaway from the conversation. Do not add any introductory phrases."
    DEFAULT_SUMMARY_METHOD = "last_msg"
    llm_config: Union[Dict, Literal[False]]

    def __init__(
        self,
        name: str,
        system_message: Optional[Union[str, List]] = "You are a helpful AI Assistant.",
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Literal["ALWAYS", "NEVER", "TERMINATE"] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Union[Dict, Literal[False]] = False,
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
        default_auto_reply: Union[str, Dict] = "",
        description: Optional[str] = None,
        chat_messages: Optional[Dict[Agent, List[Dict]]] = None,
        silent: Optional[bool] = None,
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
                - last_n_messages (Experimental, int or str): The number of messages to look back for code execution.
                    If set to 'auto', it will scan backwards through all messages arriving since the agent last spoke, which is typically the last time execution was attempted. (Default: auto)
            llm_config (dict or False or None): llm inference configuration.
                Please refer to [OpenAIWrapper.create](/docs/reference/oai/client#create)
                for available options.
                When using OpenAI or Azure OpenAI endpoints, please specify a non-empty 'model' either in `llm_config` or in each config of 'config_list' in `llm_config`.
                To disable llm-based auto reply, set to False.
                When set to None, will use self.DEFAULT_CONFIG, which defaults to False.
            default_auto_reply (str or dict): default auto reply when no code execution or llm-based reply is generated.
            description (str): a short description of the agent. This description is used by other agents
                (e.g. the GroupChatManager) to decide when to call upon this agent. (Default: system_message)
            chat_messages (dict or None): the previous chat messages that this agent had in the past with other agents.
                Can be used to give the agent a memory by providing the chat history. This will allow the agent to
                resume previous had conversations. Defaults to an empty chat history.
            silent (bool or None): (Experimental) whether to print the message sent. If None, will use the value of
                silent in each function.
        """
        # we change code_execution_config below and we have to make sure we don't change the input
        # in case of UserProxyAgent, without this we could even change the default value {}
        code_execution_config = (
            code_execution_config.copy() if hasattr(code_execution_config, "copy") else code_execution_config
        )

        self._name = name
        # a dictionary of conversations, default value is list
        if chat_messages is None:
            self._oai_messages = defaultdict(list)
        else:
            self._oai_messages = chat_messages

        self._oai_system_message = [{"content": system_message, "role": "system"}]
        self._description = description if description is not None else system_message
        self._is_termination_msg = (
            is_termination_msg
            if is_termination_msg is not None
            else (lambda x: content_str(x.get("content")) == "TERMINATE")
        )
        self.silent = silent
        # Take a copy to avoid modifying the given dict
        if isinstance(llm_config, dict):
            try:
                llm_config = copy.deepcopy(llm_config)
            except TypeError as e:
                raise TypeError(
                    "Please implement __deepcopy__ method for each value class in llm_config to support deepcopy."
                    " Refer to the docs for more details: https://microsoft.github.io/autogen/docs/topics/llm_configuration#adding-http-client-in-llm_config-for-proxy"
                ) from e

        self._validate_llm_config(llm_config)

        if logging_enabled():
            log_new_agent(self, locals())

        # Initialize standalone client cache object.
        self.client_cache = None

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
        self._human_input = []
        self.reply_at_receive = defaultdict(bool)
        self.register_reply([Agent, None], ConversableAgent.generate_oai_reply)
        self.register_reply([Agent, None], ConversableAgent.a_generate_oai_reply, ignore_async_in_sync_chat=True)

        # Setting up code execution.
        # Do not register code execution reply if code execution is disabled.
        if code_execution_config is not False:
            # If code_execution_config is None, set it to an empty dict.
            if code_execution_config is None:
                warnings.warn(
                    "Using None to signal a default code_execution_config is deprecated. "
                    "Use {} to use default or False to disable code execution.",
                    stacklevel=2,
                )
                code_execution_config = {}
            if not isinstance(code_execution_config, dict):
                raise ValueError("code_execution_config must be a dict or False.")

            # We have got a valid code_execution_config.
            self._code_execution_config = code_execution_config

            if self._code_execution_config.get("executor") is not None:
                if "use_docker" in self._code_execution_config:
                    raise ValueError(
                        "'use_docker' in code_execution_config is not valid when 'executor' is set. Use the appropriate arg in the chosen executor instead."
                    )

                if "work_dir" in self._code_execution_config:
                    raise ValueError(
                        "'work_dir' in code_execution_config is not valid when 'executor' is set. Use the appropriate arg in the chosen executor instead."
                    )

                if "timeout" in self._code_execution_config:
                    raise ValueError(
                        "'timeout' in code_execution_config is not valid when 'executor' is set. Use the appropriate arg in the chosen executor instead."
                    )

                # Use the new code executor.
                self._code_executor = CodeExecutorFactory.create(self._code_execution_config)
                self.register_reply([Agent, None], ConversableAgent._generate_code_execution_reply_using_executor)
            else:
                # Legacy code execution using code_utils.
                use_docker = self._code_execution_config.get("use_docker", None)
                use_docker = decide_use_docker(use_docker)
                check_can_use_docker_or_throw(use_docker)
                self._code_execution_config["use_docker"] = use_docker
                self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        else:
            # Code execution is disabled.
            self._code_execution_config = False

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
        self.hook_lists: Dict[str, List[Callable]] = {
            "process_last_received_message": [],
            "process_all_messages_before_reply": [],
            "process_message_before_send": [],
        }

    def _validate_llm_config(self, llm_config):
        assert llm_config in (None, False) or isinstance(
            llm_config, dict
        ), "llm_config must be a dict or False or None."
        if llm_config is None:
            llm_config = self.DEFAULT_CONFIG
        self.llm_config = self.DEFAULT_CONFIG if llm_config is None else llm_config
        # TODO: more complete validity check
        if self.llm_config in [{}, {"config_list": []}, {"config_list": [{"model": ""}]}]:
            raise ValueError(
                "When using OpenAI or Azure OpenAI endpoints, specify a non-empty 'model' either in 'llm_config' or in each config of 'config_list'."
            )
        self.client = None if self.llm_config is False else OpenAIWrapper(**self.llm_config)

    @staticmethod
    def _is_silent(agent: Agent, silent: Optional[bool] = False) -> bool:
        return agent.silent if agent.silent is not None else silent

    @property
    def name(self) -> str:
        """Get the name of the agent."""
        return self._name

    @property
    def description(self) -> str:
        """Get the description of the agent."""
        return self._description

    @description.setter
    def description(self, description: str):
        """Set the description of the agent."""
        self._description = description

    @property
    def code_executor(self) -> Optional[CodeExecutor]:
        """The code executor used by this agent. Returns None if code execution is disabled."""
        if not hasattr(self, "_code_executor"):
            return None
        return self._code_executor

    def register_reply(
        self,
        trigger: Union[Type[Agent], str, Agent, Callable[[Agent], bool], List],
        reply_func: Callable,
        position: int = 0,
        config: Optional[Any] = None,
        reset_config: Optional[Callable] = None,
        *,
        ignore_async_in_sync_chat: bool = False,
        remove_other_reply_funcs: bool = False,
    ):
        """Register a reply function.

        The reply function will be called when the trigger matches the sender.
        The function registered later will be checked earlier by default.
        To change the order, set the position to a positive integer.

        Both sync and async reply functions can be registered. The sync reply function will be triggered
        from both sync and async chats. However, an async reply function will only be triggered from async
        chats (initiated with `ConversableAgent.a_initiate_chat`). If an `async` reply function is registered
        and a chat is initialized with a sync function, `ignore_async_in_sync_chat` determines the behaviour as follows:
                if `ignore_async_in_sync_chat` is set to `False` (default value), an exception will be raised, and
                if `ignore_async_in_sync_chat` is set to `True`, the reply function will be ignored.

        Args:
            trigger (Agent class, str, Agent instance, callable, or list): the trigger.
                    If a class is provided, the reply function will be called when the sender is an instance of the class.
                    If a string is provided, the reply function will be called when the sender's name matches the string.
                    If an agent instance is provided, the reply function will be called when the sender is the agent instance.
                    If a callable is provided, the reply function will be called when the callable returns True.
                    If a list is provided, the reply function will be called when any of the triggers in the list is activated.
                    If None is provided, the reply function will be called only when the sender is None.
                    Note: Be sure to register `None` as a trigger if you would like to trigger an auto-reply function with non-empty messages and `sender=None`.
            reply_func (Callable): the reply function.
                The function takes a recipient agent, a list of messages, a sender agent and a config as input and returns a reply message.

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
            ignore_async_in_sync_chat (bool): whether to ignore the async reply function in sync chats. If `False`, an exception
                will be raised if an async reply function is registered and a chat is initialized with a sync
                function.
            remove_other_reply_funcs (bool): whether to remove other reply functions when registering this reply function.
        """
        if not isinstance(trigger, (type, str, Agent, Callable, list)):
            raise ValueError("trigger must be a class, a string, an agent, a callable or a list.")
        if remove_other_reply_funcs:
            self._reply_func_list.clear()
        self._reply_func_list.insert(
            position,
            {
                "trigger": trigger,
                "reply_func": reply_func,
                "config": copy.copy(config),
                "init_config": config,
                "reset_config": reset_config,
                "ignore_async_in_sync_chat": ignore_async_in_sync_chat and inspect.iscoroutinefunction(reply_func),
            },
        )

    def replace_reply_func(self, old_reply_func: Callable, new_reply_func: Callable):
        """Replace a registered reply function with a new one.

        Args:
            old_reply_func (Callable): the old reply function to be replaced.
            new_reply_func (Callable): the new reply function to replace the old one.
        """
        for f in self._reply_func_list:
            if f["reply_func"] == old_reply_func:
                f["reply_func"] = new_reply_func

    @staticmethod
    def _get_chats_to_run(
        chat_queue: List[Dict[str, Any]], recipient: Agent, messages: Union[str, Callable], sender: Agent, config: Any
    ) -> List[Dict[str, Any]]:
        """A simple chat reply function.
        This function initiate one or a sequence of chats between the "recipient" and the agents in the
        chat_queue.

        It extracts and returns a summary from the nested chat based on the "summary_method" in each chat in chat_queue.

        Returns:
            Tuple[bool, str]: A tuple where the first element indicates the completion of the chat, and the second element contains the summary of the last chat if any chats were initiated.
        """
        last_msg = messages[-1].get("content")
        chat_to_run = []
        for i, c in enumerate(chat_queue):
            current_c = c.copy()
            if current_c.get("sender") is None:
                current_c["sender"] = recipient
            message = current_c.get("message")
            # If message is not provided in chat_queue, we by default use the last message from the original chat history as the first message in this nested chat (for the first chat in the chat queue).
            # NOTE: This setting is prone to change.
            if message is None and i == 0:
                message = last_msg
            if callable(message):
                message = message(recipient, messages, sender, config)
            # We only run chat that has a valid message. NOTE: This is prone to change dependin on applications.
            if message:
                current_c["message"] = message
                chat_to_run.append(current_c)
        return chat_to_run

    @staticmethod
    def _summary_from_nested_chats(
        chat_queue: List[Dict[str, Any]], recipient: Agent, messages: Union[str, Callable], sender: Agent, config: Any
    ) -> Tuple[bool, Union[str, None]]:
        """A simple chat reply function.
        This function initiate one or a sequence of chats between the "recipient" and the agents in the
        chat_queue.

        It extracts and returns a summary from the nested chat based on the "summary_method" in each chat in chat_queue.

        Returns:
            Tuple[bool, str]: A tuple where the first element indicates the completion of the chat, and the second element contains the summary of the last chat if any chats were initiated.
        """
        chat_to_run = ConversableAgent._get_chats_to_run(chat_queue, recipient, messages, sender, config)
        if not chat_to_run:
            return True, None
        res = initiate_chats(chat_to_run)
        return True, res[-1].summary

    @staticmethod
    async def _a_summary_from_nested_chats(
        chat_queue: List[Dict[str, Any]], recipient: Agent, messages: Union[str, Callable], sender: Agent, config: Any
    ) -> Tuple[bool, Union[str, None]]:
        """A simple chat reply function.
        This function initiate one or a sequence of chats between the "recipient" and the agents in the
        chat_queue.

        It extracts and returns a summary from the nested chat based on the "summary_method" in each chat in chat_queue.

        Returns:
            Tuple[bool, str]: A tuple where the first element indicates the completion of the chat, and the second element contains the summary of the last chat if any chats were initiated.
        """
        chat_to_run = ConversableAgent._get_chats_to_run(chat_queue, recipient, messages, sender, config)
        if not chat_to_run:
            return True, None
        res = await a_initiate_chats(chat_to_run)
        index_of_last_chat = chat_to_run[-1]["chat_id"]
        return True, res[index_of_last_chat].summary

    def register_nested_chats(
        self,
        chat_queue: List[Dict[str, Any]],
        trigger: Union[Type[Agent], str, Agent, Callable[[Agent], bool], List],
        reply_func_from_nested_chats: Union[str, Callable] = "summary_from_nested_chats",
        position: int = 2,
        use_async: Union[bool, None] = None,
        **kwargs,
    ) -> None:
        """Register a nested chat reply function.
        Args:
            chat_queue (list): a list of chat objects to be initiated. If use_async is used, then all messages in chat_queue must have a chat-id associated with them.
            trigger (Agent class, str, Agent instance, callable, or list): refer to `register_reply` for details.
            reply_func_from_nested_chats (Callable, str): the reply function for the nested chat.
                The function takes a chat_queue for nested chat, recipient agent, a list of messages, a sender agent and a config as input and returns a reply message.
                Default to "summary_from_nested_chats", which corresponds to a built-in reply function that get summary from the nested chat_queue.
            ```python
            def reply_func_from_nested_chats(
                chat_queue: List[Dict],
                recipient: ConversableAgent,
                messages: Optional[List[Dict]] = None,
                sender: Optional[Agent] = None,
                config: Optional[Any] = None,
            ) -> Tuple[bool, Union[str, Dict, None]]:
            ```
            position (int): Ref to `register_reply` for details. Default to 2. It means we first check the termination and human reply, then check the registered nested chat reply.
            use_async: Uses a_initiate_chats internally to start nested chats. If the original chat is initiated with a_initiate_chats, you may set this to true so nested chats do not run in sync.
            kwargs: Ref to `register_reply` for details.
        """
        if use_async:
            for chat in chat_queue:
                if chat.get("chat_id") is None:
                    raise ValueError("chat_id is required for async nested chats")

        if use_async:
            if reply_func_from_nested_chats == "summary_from_nested_chats":
                reply_func_from_nested_chats = self._a_summary_from_nested_chats
            if not callable(reply_func_from_nested_chats) or not inspect.iscoroutinefunction(
                reply_func_from_nested_chats
            ):
                raise ValueError("reply_func_from_nested_chats must be a callable and a coroutine")

            async def wrapped_reply_func(recipient, messages=None, sender=None, config=None):
                return await reply_func_from_nested_chats(chat_queue, recipient, messages, sender, config)

        else:
            if reply_func_from_nested_chats == "summary_from_nested_chats":
                reply_func_from_nested_chats = self._summary_from_nested_chats
            if not callable(reply_func_from_nested_chats):
                raise ValueError("reply_func_from_nested_chats must be a callable")

            def wrapped_reply_func(recipient, messages=None, sender=None, config=None):
                return reply_func_from_nested_chats(chat_queue, recipient, messages, sender, config)

        functools.update_wrapper(wrapped_reply_func, reply_func_from_nested_chats)

        self.register_reply(
            trigger,
            wrapped_reply_func,
            position,
            kwargs.get("config"),
            kwargs.get("reset_config"),
            ignore_async_in_sync_chat=(
                not use_async if use_async is not None else kwargs.get("ignore_async_in_sync_chat")
            ),
        )

    @property
    def system_message(self) -> str:
        """Return the system message."""
        return self._oai_system_message[0]["content"]

    def update_system_message(self, system_message: str) -> None:
        """Update the system message.

        Args:
            system_message (str): system message for the ChatCompletion inference.
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

    def chat_messages_for_summary(self, agent: Agent) -> List[Dict]:
        """A list of messages as a conversation to summarize."""
        return self._oai_messages[agent]

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

    def _append_oai_message(self, message: Union[Dict, str], role, conversation_id: Agent, is_sending: bool) -> bool:
        """Append a message to the ChatCompletion conversation.

        If the message received is a string, it will be put in the "content" field of the new dictionary.
        If the message received is a dictionary but does not have any of the three fields "content", "function_call", or "tool_calls",
            this message is not a valid ChatCompletion message.
        If only "function_call" or "tool_calls" is provided, "content" will be set to None if not provided, and the role of the message will be forced "assistant".

        Args:
            message (dict or str): message to be appended to the ChatCompletion conversation.
            role (str): role of the message, can be "assistant" or "function".
            conversation_id (Agent): id of the conversation, should be the recipient or sender.
            is_sending (bool): If the agent (aka self) is sending to the conversation_id agent, otherwise receiving.

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
        elif "override_role" in message:
            # If we have a direction to override the role then set the
            # role accordingly. Used to customise the role for the
            # select speaker prompt.
            oai_message["role"] = message.get("override_role")
        else:
            oai_message["role"] = role

        if oai_message.get("function_call", False) or oai_message.get("tool_calls", False):
            oai_message["role"] = "assistant"  # only messages with role 'assistant' can have a function call.
        elif "name" not in oai_message:
            # If we don't have a name field, append it
            if is_sending:
                oai_message["name"] = self.name
            else:
                oai_message["name"] = conversation_id.name

        self._oai_messages[conversation_id].append(oai_message)

        return True

    def _process_message_before_send(
        self, message: Union[Dict, str], recipient: Agent, silent: bool
    ) -> Union[Dict, str]:
        """Process the message before sending it to the recipient."""
        hook_list = self.hook_lists["process_message_before_send"]
        for hook in hook_list:
            message = hook(
                sender=self, message=message, recipient=recipient, silent=ConversableAgent._is_silent(self, silent)
            )
        return message

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
        message = self._process_message_before_send(message, recipient, ConversableAgent._is_silent(self, silent))
        # When the agent composes and sends the message, the role of the message is "assistant"
        # unless it's "function".
        valid = self._append_oai_message(message, "assistant", recipient, is_sending=True)
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
        message = self._process_message_before_send(message, recipient, ConversableAgent._is_silent(self, silent))
        # When the agent composes and sends the message, the role of the message is "assistant"
        # unless it's "function".
        valid = self._append_oai_message(message, "assistant", recipient, is_sending=True)
        if valid:
            await recipient.a_receive(message, self, request_reply, silent)
        else:
            raise ValueError(
                "Message can't be converted into a valid ChatCompletion message. Either content or function_call must be provided."
            )

    def _print_received_message(self, message: Union[Dict, str], sender: Agent):
        iostream = IOStream.get_default()
        # print the message received
        iostream.print(colored(sender.name, "yellow"), "(to", f"{self.name}):\n", flush=True)
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
            id = message.get(id_key, "No id found")
            func_print = f"***** Response from calling {message['role']} ({id}) *****"
            iostream.print(colored(func_print, "green"), flush=True)
            iostream.print(message["content"], flush=True)
            iostream.print(colored("*" * len(func_print), "green"), flush=True)
        else:
            content = message.get("content")
            if content is not None:
                if "context" in message:
                    content = OpenAIWrapper.instantiate(
                        content,
                        message["context"],
                        self.llm_config and self.llm_config.get("allow_format_str_template", False),
                    )
                iostream.print(content_str(content), flush=True)
            if "function_call" in message and message["function_call"]:
                function_call = dict(message["function_call"])
                func_print = (
                    f"***** Suggested function call: {function_call.get('name', '(No function name found)')} *****"
                )
                iostream.print(colored(func_print, "green"), flush=True)
                iostream.print(
                    "Arguments: \n",
                    function_call.get("arguments", "(No arguments found)"),
                    flush=True,
                    sep="",
                )
                iostream.print(colored("*" * len(func_print), "green"), flush=True)
            if "tool_calls" in message and message["tool_calls"]:
                for tool_call in message["tool_calls"]:
                    id = tool_call.get("id", "No tool call id found")
                    function_call = dict(tool_call.get("function", {}))
                    func_print = f"***** Suggested tool call ({id}): {function_call.get('name', '(No function name found)')} *****"
                    iostream.print(colored(func_print, "green"), flush=True)
                    iostream.print(
                        "Arguments: \n",
                        function_call.get("arguments", "(No arguments found)"),
                        flush=True,
                        sep="",
                    )
                    iostream.print(colored("*" * len(func_print), "green"), flush=True)

        iostream.print("\n", "-" * 80, flush=True, sep="")

    def _process_received_message(self, message: Union[Dict, str], sender: Agent, silent: bool):
        # When the agent receives a message, the role of the message is "user". (If 'role' exists and is 'function', it will remain unchanged.)
        valid = self._append_oai_message(message, "user", sender, is_sending=False)
        if logging_enabled():
            log_event(self, "received_message", message=message, sender=sender.name, valid=valid)

        if not valid:
            raise ValueError(
                "Received message can't be converted into a valid ChatCompletion message. Either content or function_call must be provided."
            )

        if not ConversableAgent._is_silent(sender, silent):
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

    def _prepare_chat(
        self,
        recipient: "ConversableAgent",
        clear_history: bool,
        prepare_recipient: bool = True,
        reply_at_receive: bool = True,
    ) -> None:
        self.reset_consecutive_auto_reply_counter(recipient)
        self.reply_at_receive[recipient] = reply_at_receive
        if clear_history:
            self.clear_history(recipient)
            self._human_input = []
        if prepare_recipient:
            recipient._prepare_chat(self, clear_history, False, reply_at_receive)

    def _raise_exception_on_async_reply_functions(self) -> None:
        """Raise an exception if any async reply functions are registered.

        Raises:
            RuntimeError: if any async reply functions are registered.
        """
        reply_functions = {
            f["reply_func"] for f in self._reply_func_list if not f.get("ignore_async_in_sync_chat", False)
        }

        async_reply_functions = [f for f in reply_functions if inspect.iscoroutinefunction(f)]
        if async_reply_functions:
            msg = (
                "Async reply functions can only be used with ConversableAgent.a_initiate_chat(). The following async reply functions are found: "
                + ", ".join([f.__name__ for f in async_reply_functions])
            )

            raise RuntimeError(msg)

    def initiate_chat(
        self,
        recipient: "ConversableAgent",
        clear_history: bool = True,
        silent: Optional[bool] = False,
        cache: Optional[AbstractCache] = None,
        max_turns: Optional[int] = None,
        summary_method: Optional[Union[str, Callable]] = DEFAULT_SUMMARY_METHOD,
        summary_args: Optional[dict] = {},
        message: Optional[Union[Dict, str, Callable]] = None,
        **kwargs,
    ) -> ChatResult:
        """Initiate a chat with the recipient agent.

        Reset the consecutive auto reply counter.
        If `clear_history` is True, the chat history with the recipient agent will be cleared.


        Args:
            recipient: the recipient agent.
            clear_history (bool): whether to clear the chat history with the agent. Default is True.
            silent (bool or None): (Experimental) whether to print the messages for this conversation. Default is False.
            cache (AbstractCache or None): the cache client to be used for this conversation. Default is None.
            max_turns (int or None): the maximum number of turns for the chat between the two agents. One turn means one conversation round trip. Note that this is different from
                [max_consecutive_auto_reply](#max_consecutive_auto_reply) which is the maximum number of consecutive auto replies; and it is also different from [max_rounds in GroupChat](./groupchat#groupchat-objects) which is the maximum number of rounds in a group chat session.
                If max_turns is set to None, the chat will continue until a termination condition is met. Default is None.
            summary_method (str or callable): a method to get a summary from the chat. Default is DEFAULT_SUMMARY_METHOD, i.e., "last_msg".

            Supported strings are "last_msg" and "reflection_with_llm":
                - when set to "last_msg", it returns the last message of the dialog as the summary.
                - when set to "reflection_with_llm", it returns a summary extracted using an llm client.
                    `llm_config` must be set in either the recipient or sender.

            A callable summary_method should take the recipient and sender agent in a chat as input and return a string of summary. E.g.,

            ```python
            def my_summary_method(
                sender: ConversableAgent,
                recipient: ConversableAgent,
                summary_args: dict,
            ):
                return recipient.last_message(sender)["content"]
            ```
            summary_args (dict): a dictionary of arguments to be passed to the summary_method.
                One example key is "summary_prompt", and value is a string of text used to prompt a LLM-based agent (the sender or receiver agent) to reflect
                on the conversation and extract a summary when summary_method is "reflection_with_llm".
                The default summary_prompt is DEFAULT_SUMMARY_PROMPT, i.e., "Summarize takeaway from the conversation. Do not add any introductory phrases. If the intended request is NOT properly addressed, please point it out."
                Another available key is "summary_role", which is the role of the message sent to the agent in charge of summarizing. Default is "system".
            message (str, dict or Callable): the initial message to be sent to the recipient. Needs to be provided. Otherwise, input() will be called to get the initial message.
                - If a string or a dict is provided, it will be used as the initial message.        `generate_init_message` is called to generate the initial message for the agent based on this string and the context.
                    If dict, it may contain the following reserved fields (either content or tool_calls need to be provided).

                        1. "content": content of the message, can be None.
                        2. "function_call": a dictionary containing the function name and arguments. (deprecated in favor of "tool_calls")
                        3. "tool_calls": a list of dictionaries containing the function name and arguments.
                        4. "role": role of the message, can be "assistant", "user", "function".
                            This field is only needed to distinguish between "function" or "assistant"/"user".
                        5. "name": In most cases, this field is not needed. When the role is "function", this field is needed to indicate the function name.
                        6. "context" (dict): the context of the message, which will be passed to
                            [OpenAIWrapper.create](../oai/client#create).

                - If a callable is provided, it will be called to get the initial message in the form of a string or a dict.
                    If the returned type is dict, it may contain the reserved fields mentioned above.

                    Example of a callable message (returning a string):

            ```python
            def my_message(sender: ConversableAgent, recipient: ConversableAgent, context: dict) -> Union[str, Dict]:
                carryover = context.get("carryover", "")
                if isinstance(message, list):
                    carryover = carryover[-1]
                final_msg = "Write a blogpost." + "\\nContext: \\n" + carryover
                return final_msg
            ```

                    Example of a callable message (returning a dict):

            ```python
            def my_message(sender: ConversableAgent, recipient: ConversableAgent, context: dict) -> Union[str, Dict]:
                final_msg = {}
                carryover = context.get("carryover", "")
                if isinstance(message, list):
                    carryover = carryover[-1]
                final_msg["content"] = "Write a blogpost." + "\\nContext: \\n" + carryover
                final_msg["context"] = {"prefix": "Today I feel"}
                return final_msg
            ```
            **kwargs: any additional information. It has the following reserved fields:
                - "carryover": a string or a list of string to specify the carryover information to be passed to this chat.
                    If provided, we will combine this carryover (by attaching a "context: " string and the carryover content after the message content) with the "message" content when generating the initial chat
                    message in `generate_init_message`.
                - "verbose": a boolean to specify whether to print the message and carryover in a chat. Default is False.

        Raises:
            RuntimeError: if any async reply functions are registered and not ignored in sync chat.

        Returns:
            ChatResult: an ChatResult object.
        """
        _chat_info = locals().copy()
        _chat_info["sender"] = self
        consolidate_chat_info(_chat_info, uniform_sender=self)
        for agent in [self, recipient]:
            agent._raise_exception_on_async_reply_functions()
            agent.previous_cache = agent.client_cache
            agent.client_cache = cache
        if isinstance(max_turns, int):
            self._prepare_chat(recipient, clear_history, reply_at_receive=False)
            for _ in range(max_turns):
                if _ == 0:
                    if isinstance(message, Callable):
                        msg2send = message(_chat_info["sender"], _chat_info["recipient"], kwargs)
                    else:
                        msg2send = self.generate_init_message(message, **kwargs)
                else:
                    msg2send = self.generate_reply(messages=self.chat_messages[recipient], sender=recipient)
                if msg2send is None:
                    break
                self.send(msg2send, recipient, request_reply=True, silent=silent)
        else:
            self._prepare_chat(recipient, clear_history)
            if isinstance(message, Callable):
                msg2send = message(_chat_info["sender"], _chat_info["recipient"], kwargs)
            else:
                msg2send = self.generate_init_message(message, **kwargs)
            self.send(msg2send, recipient, silent=silent)
        summary = self._summarize_chat(
            summary_method,
            summary_args,
            recipient,
            cache=cache,
        )
        for agent in [self, recipient]:
            agent.client_cache = agent.previous_cache
            agent.previous_cache = None
        chat_result = ChatResult(
            chat_history=self.chat_messages[recipient],
            summary=summary,
            cost=gather_usage_summary([self, recipient]),
            human_input=self._human_input,
        )
        return chat_result

    async def a_initiate_chat(
        self,
        recipient: "ConversableAgent",
        clear_history: bool = True,
        silent: Optional[bool] = False,
        cache: Optional[AbstractCache] = None,
        max_turns: Optional[int] = None,
        summary_method: Optional[Union[str, Callable]] = DEFAULT_SUMMARY_METHOD,
        summary_args: Optional[dict] = {},
        message: Optional[Union[str, Callable]] = None,
        **kwargs,
    ) -> ChatResult:
        """(async) Initiate a chat with the recipient agent.

        Reset the consecutive auto reply counter.
        If `clear_history` is True, the chat history with the recipient agent will be cleared.
        `a_generate_init_message` is called to generate the initial message for the agent.

        Args: Please refer to `initiate_chat`.

        Returns:
            ChatResult: an ChatResult object.
        """
        _chat_info = locals().copy()
        _chat_info["sender"] = self
        consolidate_chat_info(_chat_info, uniform_sender=self)
        for agent in [self, recipient]:
            agent.previous_cache = agent.client_cache
            agent.client_cache = cache
        if isinstance(max_turns, int):
            self._prepare_chat(recipient, clear_history, reply_at_receive=False)
            for _ in range(max_turns):
                if _ == 0:
                    if isinstance(message, Callable):
                        msg2send = message(_chat_info["sender"], _chat_info["recipient"], kwargs)
                    else:
                        msg2send = await self.a_generate_init_message(message, **kwargs)
                else:
                    msg2send = await self.a_generate_reply(messages=self.chat_messages[recipient], sender=recipient)
                if msg2send is None:
                    break
                await self.a_send(msg2send, recipient, request_reply=True, silent=silent)
        else:
            self._prepare_chat(recipient, clear_history)
            if isinstance(message, Callable):
                msg2send = message(_chat_info["sender"], _chat_info["recipient"], kwargs)
            else:
                msg2send = await self.a_generate_init_message(message, **kwargs)
            await self.a_send(msg2send, recipient, silent=silent)
        summary = self._summarize_chat(
            summary_method,
            summary_args,
            recipient,
            cache=cache,
        )
        for agent in [self, recipient]:
            agent.client_cache = agent.previous_cache
            agent.previous_cache = None
        chat_result = ChatResult(
            chat_history=self.chat_messages[recipient],
            summary=summary,
            cost=gather_usage_summary([self, recipient]),
            human_input=self._human_input,
        )
        return chat_result

    def _summarize_chat(
        self,
        summary_method,
        summary_args,
        recipient: Optional[Agent] = None,
        cache: Optional[AbstractCache] = None,
    ) -> str:
        """Get a chat summary from an agent participating in a chat.

        Args:
            summary_method (str or callable): the summary_method to get the summary.
                The callable summary_method should take the recipient and sender agent in a chat as input and return a string of summary. E.g,
                ```python
                def my_summary_method(
                    sender: ConversableAgent,
                    recipient: ConversableAgent,
                    summary_args: dict,
                ):
                    return recipient.last_message(sender)["content"]
                ```
            summary_args (dict): a dictionary of arguments to be passed to the summary_method.
            recipient: the recipient agent in a chat.
            prompt (str): the prompt used to get a summary when summary_method is "reflection_with_llm".

        Returns:
            str: a chat summary from the agent.
        """
        summary = ""
        if summary_method is None:
            return summary
        if "cache" not in summary_args:
            summary_args["cache"] = cache
        if summary_method == "reflection_with_llm":
            summary_method = self._reflection_with_llm_as_summary
        elif summary_method == "last_msg":
            summary_method = self._last_msg_as_summary

        if isinstance(summary_method, Callable):
            summary = summary_method(self, recipient, summary_args)
        else:
            raise ValueError(
                "If not None, the summary_method must be a string from [`reflection_with_llm`, `last_msg`] or a callable."
            )
        return summary

    @staticmethod
    def _last_msg_as_summary(sender, recipient, summary_args) -> str:
        """Get a chat summary from the last message of the recipient."""
        summary = ""
        try:
            content = recipient.last_message(sender)["content"]
            if isinstance(content, str):
                summary = content.replace("TERMINATE", "")
            elif isinstance(content, list):
                # Remove the `TERMINATE` word in the content list.
                summary = "\n".join(
                    x["text"].replace("TERMINATE", "") for x in content if isinstance(x, dict) and "text" in x
                )
        except (IndexError, AttributeError) as e:
            warnings.warn(f"Cannot extract summary using last_msg: {e}. Using an empty str as summary.", UserWarning)
        return summary

    @staticmethod
    def _reflection_with_llm_as_summary(sender, recipient, summary_args):
        prompt = summary_args.get("summary_prompt")
        prompt = ConversableAgent.DEFAULT_SUMMARY_PROMPT if prompt is None else prompt
        if not isinstance(prompt, str):
            raise ValueError("The summary_prompt must be a string.")
        msg_list = recipient.chat_messages_for_summary(sender)
        agent = sender if recipient is None else recipient
        role = summary_args.get("summary_role", None)
        if role and not isinstance(role, str):
            raise ValueError("The summary_role in summary_arg must be a string.")
        try:
            summary = sender._reflection_with_llm(
                prompt, msg_list, llm_agent=agent, cache=summary_args.get("cache"), role=role
            )
        except BadRequestError as e:
            warnings.warn(
                f"Cannot extract summary using reflection_with_llm: {e}. Using an empty str as summary.", UserWarning
            )
            summary = ""
        return summary

    def _reflection_with_llm(
        self,
        prompt,
        messages,
        llm_agent: Optional[Agent] = None,
        cache: Optional[AbstractCache] = None,
        role: Union[str, None] = None,
    ) -> str:
        """Get a chat summary using reflection with an llm client based on the conversation history.

        Args:
            prompt (str): The prompt (in this method it is used as system prompt) used to get the summary.
            messages (list): The messages generated as part of a chat conversation.
            llm_agent: the agent with an llm client.
            cache (AbstractCache or None): the cache client to be used for this conversation.
            role (str): the role of the message, usually "system" or "user". Default is "system".
        """
        if not role:
            role = "system"

        system_msg = [
            {
                "role": role,
                "content": prompt,
            }
        ]

        messages = messages + system_msg
        if llm_agent and llm_agent.client is not None:
            llm_client = llm_agent.client
        elif self.client is not None:
            llm_client = self.client
        else:
            raise ValueError("No OpenAIWrapper client is found.")
        response = self._generate_oai_reply_from_client(llm_client=llm_client, messages=messages, cache=cache)
        return response

    def _check_chat_queue_for_sender(self, chat_queue: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Check the chat queue and add the "sender" key if it's missing.

        Args:
            chat_queue (List[Dict[str, Any]]): A list of dictionaries containing chat information.

        Returns:
            List[Dict[str, Any]]: A new list of dictionaries with the "sender" key added if it was missing.
        """
        chat_queue_with_sender = []
        for chat_info in chat_queue:
            if chat_info.get("sender") is None:
                chat_info["sender"] = self
            chat_queue_with_sender.append(chat_info)
        return chat_queue_with_sender

    def initiate_chats(self, chat_queue: List[Dict[str, Any]]) -> List[ChatResult]:
        """(Experimental) Initiate chats with multiple agents.

        Args:
            chat_queue (List[Dict]): a list of dictionaries containing the information of the chats.
                Each dictionary should contain the input arguments for [`initiate_chat`](conversable_agent#initiate_chat)

        Returns: a list of ChatResult objects corresponding to the finished chats in the chat_queue.
        """
        _chat_queue = self._check_chat_queue_for_sender(chat_queue)
        self._finished_chats = initiate_chats(_chat_queue)
        return self._finished_chats

    async def a_initiate_chats(self, chat_queue: List[Dict[str, Any]]) -> Dict[int, ChatResult]:
        _chat_queue = self._check_chat_queue_for_sender(chat_queue)
        self._finished_chats = await a_initiate_chats(_chat_queue)
        return self._finished_chats

    def get_chat_results(self, chat_index: Optional[int] = None) -> Union[List[ChatResult], ChatResult]:
        """A summary from the finished chats of particular agents."""
        if chat_index is not None:
            return self._finished_chats[chat_index]
        else:
            return self._finished_chats

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

    def clear_history(self, recipient: Optional[Agent] = None, nr_messages_to_preserve: Optional[int] = None):
        """Clear the chat history of the agent.

        Args:
            recipient: the agent with whom the chat history to clear. If None, clear the chat history with all agents.
            nr_messages_to_preserve: the number of newest messages to preserve in the chat history.
        """
        iostream = IOStream.get_default()
        if recipient is None:
            if nr_messages_to_preserve:
                for key in self._oai_messages:
                    nr_messages_to_preserve_internal = nr_messages_to_preserve
                    # if breaking history between function call and function response, save function call message
                    # additionally, otherwise openai will return error
                    first_msg_to_save = self._oai_messages[key][-nr_messages_to_preserve_internal]
                    if "tool_responses" in first_msg_to_save:
                        nr_messages_to_preserve_internal += 1
                        iostream.print(
                            f"Preserving one more message for {self.name} to not divide history between tool call and "
                            f"tool response."
                        )
                    # Remove messages from history except last `nr_messages_to_preserve` messages.
                    self._oai_messages[key] = self._oai_messages[key][-nr_messages_to_preserve_internal:]
            else:
                self._oai_messages.clear()
        else:
            self._oai_messages[recipient].clear()
            if nr_messages_to_preserve:
                iostream.print(
                    colored(
                        "WARNING: `nr_preserved_messages` is ignored when clearing chat history with a specific agent.",
                        "yellow",
                    ),
                    flush=True,
                )

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
        extracted_response = self._generate_oai_reply_from_client(
            client, self._oai_system_message + messages, self.client_cache
        )
        return (False, None) if extracted_response is None else (True, extracted_response)

    def _generate_oai_reply_from_client(self, llm_client, messages, cache) -> Union[str, Dict, None]:
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
        response = llm_client.create(
            context=messages[-1].pop("context", None), messages=all_messages, cache=cache, agent=self
        )
        extracted_response = llm_client.extract_text_or_completion_object(response)[0]

        if extracted_response is None:
            warnings.warn(f"Extracted_response from {response} is None.", UserWarning)
            return None
        # ensure function and tool calls will be accepted when sent back to the LLM
        if not isinstance(extracted_response, str) and hasattr(extracted_response, "model_dump"):
            extracted_response = model_dump(extracted_response)
        if isinstance(extracted_response, dict):
            if extracted_response.get("function_call"):
                extracted_response["function_call"]["name"] = self._normalize_name(
                    extracted_response["function_call"]["name"]
                )
            for tool_call in extracted_response.get("tool_calls") or []:
                tool_call["function"]["name"] = self._normalize_name(tool_call["function"]["name"])
                # Remove id and type if they are not present.
                # This is to make the tool call object compatible with Mistral API.
                if tool_call.get("id") is None:
                    tool_call.pop("id")
                if tool_call.get("type") is None:
                    tool_call.pop("type")
        return extracted_response

    async def a_generate_oai_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate a reply using autogen.oai asynchronously."""
        iostream = IOStream.get_default()

        def _generate_oai_reply(
            self, iostream: IOStream, *args: Any, **kwargs: Any
        ) -> Tuple[bool, Union[str, Dict, None]]:
            with IOStream.set_default(iostream):
                return self.generate_oai_reply(*args, **kwargs)

        return await asyncio.get_event_loop().run_in_executor(
            None,
            functools.partial(
                _generate_oai_reply, self=self, iostream=iostream, messages=messages, sender=sender, config=config
            ),
        )

    def _generate_code_execution_reply_using_executor(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Union[Dict, Literal[False]]] = None,
    ):
        """Generate a reply using code executor."""
        iostream = IOStream.get_default()

        if config is not None:
            raise ValueError("config is not supported for _generate_code_execution_reply_using_executor.")
        if self._code_execution_config is False:
            return False, None
        if messages is None:
            messages = self._oai_messages[sender]
        last_n_messages = self._code_execution_config.get("last_n_messages", "auto")

        if not (isinstance(last_n_messages, (int, float)) and last_n_messages >= 0) and last_n_messages != "auto":
            raise ValueError("last_n_messages must be either a non-negative integer, or the string 'auto'.")

        num_messages_to_scan = last_n_messages
        if last_n_messages == "auto":
            # Find when the agent last spoke
            num_messages_to_scan = 0
            for message in reversed(messages):
                if "role" not in message:
                    break
                elif message["role"] != "user":
                    break
                else:
                    num_messages_to_scan += 1
        num_messages_to_scan = min(len(messages), num_messages_to_scan)
        messages_to_scan = messages[-num_messages_to_scan:]

        # iterate through the last n messages in reverse
        # if code blocks are found, execute the code blocks and return the output
        # if no code blocks are found, continue
        for message in reversed(messages_to_scan):
            if not message["content"]:
                continue
            code_blocks = self._code_executor.code_extractor.extract_code_blocks(message["content"])
            if len(code_blocks) == 0:
                continue

            num_code_blocks = len(code_blocks)
            if num_code_blocks == 1:
                iostream.print(
                    colored(
                        f"\n>>>>>>>> EXECUTING CODE BLOCK (inferred language is {code_blocks[0].language})...",
                        "red",
                    ),
                    flush=True,
                )
            else:
                iostream.print(
                    colored(
                        f"\n>>>>>>>> EXECUTING {num_code_blocks} CODE BLOCKS (inferred languages are [{', '.join([x.language for x in code_blocks])}])...",
                        "red",
                    ),
                    flush=True,
                )

            # found code blocks, execute code.
            code_result = self._code_executor.execute_code_blocks(code_blocks)
            exitcode2str = "execution succeeded" if code_result.exit_code == 0 else "execution failed"
            return True, f"exitcode: {code_result.exit_code} ({exitcode2str})\nCode output: {code_result.output}"

        return False, None

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
                try:
                    # get the running loop if it was already created
                    loop = asyncio.get_running_loop()
                    close_loop = False
                except RuntimeError:
                    # create a loop if there is no running loop
                    loop = asyncio.new_event_loop()
                    close_loop = True

                _, func_return = loop.run_until_complete(self.a_execute_function(func_call))
                if close_loop:
                    loop.close()
            else:
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
        func_call = message.get("function_call")
        if func_call:
            func_name = func_call.get("name", "")
            func = self._function_map.get(func_name, None)
            if func and inspect.iscoroutinefunction(func):
                _, func_return = await self.a_execute_function(func_call)
            else:
                _, func_return = self.execute_function(func_call)
            return True, func_return

        return False, None

    def _str_for_tool_response(self, tool_response):
        return str(tool_response.get("content", ""))

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
            function_call = tool_call.get("function", {})
            func = self._function_map.get(function_call.get("name", None), None)
            if inspect.iscoroutinefunction(func):
                try:
                    # get the running loop if it was already created
                    loop = asyncio.get_running_loop()
                    close_loop = False
                except RuntimeError:
                    # create a loop if there is no running loop
                    loop = asyncio.new_event_loop()
                    close_loop = True

                _, func_return = loop.run_until_complete(self.a_execute_function(function_call))
                if close_loop:
                    loop.close()
            else:
                _, func_return = self.execute_function(function_call)
            content = func_return.get("content", "")
            if content is None:
                content = ""
            tool_call_id = tool_call.get("id", None)
            if tool_call_id is not None:
                tool_call_response = {
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "content": content,
                }
            else:
                # Do not include tool_call_id if it is not present.
                # This is to make the tool call object compatible with Mistral API.
                tool_call_response = {
                    "role": "tool",
                    "content": content,
                }
            tool_returns.append(tool_call_response)
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
        iostream = IOStream.get_default()

        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender] if sender else []
        message = messages[-1]
        reply = ""
        no_human_input_msg = ""
        sender_name = "the sender" if sender is None else sender.name
        if self.human_input_mode == "ALWAYS":
            reply = self.get_human_input(
                f"Replying as {self.name}. Provide feedback to {sender_name}. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "
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
                        f"Please give feedback to {sender_name}. Press enter or type 'exit' to stop the conversation: "
                        if terminate
                        else f"Please give feedback to {sender_name}. Press enter to skip and use auto-reply, or type 'exit' to stop the conversation: "
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
                        f"Please give feedback to {sender_name}. Press enter or type 'exit' to stop the conversation: "
                    )
                    no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
                    # if the human input is empty, and the message is a termination message, then we will terminate the conversation
                    reply = reply or "exit"

        # print the no_human_input_msg
        if no_human_input_msg:
            iostream.print(colored(f"\n>>>>>>>> {no_human_input_msg}", "red"), flush=True)

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
            iostream.print(colored("\n>>>>>>>> USING AUTO REPLY...", "red"), flush=True)

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
        iostream = IOStream.get_default()

        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender] if sender else []
        message = messages[-1] if messages else {}
        reply = ""
        no_human_input_msg = ""
        sender_name = "the sender" if sender is None else sender.name
        if self.human_input_mode == "ALWAYS":
            reply = await self.a_get_human_input(
                f"Replying as {self.name}. Provide feedback to {sender_name}. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "
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
                        f"Please give feedback to {sender_name}. Press enter or type 'exit' to stop the conversation: "
                        if terminate
                        else f"Please give feedback to {sender_name}. Press enter to skip and use auto-reply, or type 'exit' to stop the conversation: "
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
                        f"Please give feedback to {sender_name}. Press enter or type 'exit' to stop the conversation: "
                    )
                    no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
                    # if the human input is empty, and the message is a termination message, then we will terminate the conversation
                    reply = reply or "exit"

        # print the no_human_input_msg
        if no_human_input_msg:
            iostream.print(colored(f"\n>>>>>>>> {no_human_input_msg}", "red"), flush=True)

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
            iostream.print(colored("\n>>>>>>>> USING AUTO REPLY...", "red"), flush=True)

        return False, None

    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional["Agent"] = None,
        **kwargs: Any,
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
            sender: sender of an Agent instance.

        Additional keyword arguments:
            exclude (List[Callable]): a list of reply functions to be excluded.

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
        messages = self.process_last_received_message(messages)

        # Call the hookable method that gives registered hooks a chance to process all messages.
        # Message modifications do not affect the incoming messages or self._oai_messages.
        messages = self.process_all_messages_before_reply(messages)

        for reply_func_tuple in self._reply_func_list:
            reply_func = reply_func_tuple["reply_func"]
            if "exclude" in kwargs and reply_func in kwargs["exclude"]:
                continue
            if inspect.iscoroutinefunction(reply_func):
                continue
            if self._match_trigger(reply_func_tuple["trigger"], sender):
                final, reply = reply_func(self, messages=messages, sender=sender, config=reply_func_tuple["config"])
                if logging_enabled():
                    log_event(
                        self,
                        "reply_func_executed",
                        reply_func_module=reply_func.__module__,
                        reply_func_name=reply_func.__name__,
                        final=final,
                        reply=reply,
                    )
                if final:
                    return reply
        return self._default_auto_reply

    async def a_generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional["Agent"] = None,
        **kwargs: Any,
    ) -> Union[str, Dict[str, Any], None]:
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
            sender: sender of an Agent instance.

        Additional keyword arguments:
            exclude (List[Callable]): a list of reply functions to be excluded.

        Returns:
            str or dict or None: reply. None if no reply is generated.
        """
        if all((messages is None, sender is None)):
            error_msg = f"Either {messages=} or {sender=} must be provided."
            logger.error(error_msg)
            raise AssertionError(error_msg)

        if messages is None:
            messages = self._oai_messages[sender]

        # Call the hookable method that gives registered hooks a chance to process all messages.
        # Message modifications do not affect the incoming messages or self._oai_messages.
        messages = self.process_all_messages_before_reply(messages)

        # Call the hookable method that gives registered hooks a chance to process the last message.
        # Message modifications do not affect the incoming messages or self._oai_messages.
        messages = self.process_last_received_message(messages)

        for reply_func_tuple in self._reply_func_list:
            reply_func = reply_func_tuple["reply_func"]
            if "exclude" in kwargs and reply_func in kwargs["exclude"]:
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

    def _match_trigger(self, trigger: Union[None, str, type, Agent, Callable, List], sender: Optional[Agent]) -> bool:
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
            if sender is None:
                raise SenderRequired()
            return trigger == sender.name
        elif isinstance(trigger, type):
            return isinstance(sender, trigger)
        elif isinstance(trigger, Agent):
            # return True if the sender is the same type (class) as the trigger
            return trigger == sender
        elif isinstance(trigger, Callable):
            rst = trigger(sender)
            assert isinstance(rst, bool), f"trigger {trigger} must return a boolean value."
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
        iostream = IOStream.get_default()

        reply = iostream.input(prompt)
        self._human_input.append(reply)
        return reply

    async def a_get_human_input(self, prompt: str) -> str:
        """(Async) Get human input.

        Override this method to customize the way to get human input.

        Args:
            prompt (str): prompt for the human input.

        Returns:
            str: human input.
        """
        loop = asyncio.get_running_loop()
        reply = await loop.run_in_executor(None, functools.partial(self.get_human_input, prompt))
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
        iostream = IOStream.get_default()

        logs_all = ""
        for i, code_block in enumerate(code_blocks):
            lang, code = code_block
            if not lang:
                lang = infer_lang(code)
            iostream.print(
                colored(
                    f"\n>>>>>>>> EXECUTING CODE BLOCK {i} (inferred language is {lang})...",
                    "red",
                ),
                flush=True,
            )
            if lang in ["bash", "shell", "sh"]:
                exitcode, logs, image = self.run_code(code, lang=lang, **self._code_execution_config)
            elif lang in PYTHON_VARIANTS:
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

        2. this function also handles JSON escape sequences inside quotes.
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
        iostream = IOStream.get_default()

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
                content = f"Error: {e}\n The argument must be in JSON format."

            # Try to execute the function
            if arguments is not None:
                iostream.print(
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
            iostream.print(
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
        iostream = IOStream.get_default()

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
                content = f"Error: {e}\n The argument must be in JSON format."

            # Try to execute the function
            if arguments is not None:
                iostream.print(
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

    def generate_init_message(self, message: Union[Dict, str, None], **kwargs) -> Union[str, Dict]:
        """Generate the initial message for the agent.
        If message is None, input() will be called to get the initial message.

        Args:
            message (str or None): the message to be processed.
            **kwargs: any additional information. It has the following reserved fields:
                "carryover": a string or a list of string to specify the carryover information to be passed to this chat. It can be a string or a list of string.
                    If provided, we will combine this carryover with the "message" content when generating the initial chat
                    message.
        Returns:
            str or dict: the processed message.
        """
        if message is None:
            message = self.get_human_input(">")

        return self._handle_carryover(message, kwargs)

    def _handle_carryover(self, message: Union[str, Dict], kwargs: dict) -> Union[str, Dict]:
        if not kwargs.get("carryover"):
            return message

        if isinstance(message, str):
            return self._process_carryover(message, kwargs)

        elif isinstance(message, dict):
            if isinstance(message.get("content"), str):
                # Makes sure the original message is not mutated
                message = message.copy()
                message["content"] = self._process_carryover(message["content"], kwargs)
            elif isinstance(message.get("content"), list):
                # Makes sure the original message is not mutated
                message = message.copy()
                message["content"] = self._process_multimodal_carryover(message["content"], kwargs)
        else:
            raise InvalidCarryOverType("Carryover should be a string or a list of strings.")

        return message

    def _process_carryover(self, content: str, kwargs: dict) -> str:
        # Makes sure there's a carryover
        if not kwargs.get("carryover"):
            return content

        # if carryover is string
        if isinstance(kwargs["carryover"], str):
            content += "\nContext: \n" + kwargs["carryover"]
        elif isinstance(kwargs["carryover"], list):
            content += "\nContext: \n" + ("\n").join([_post_process_carryover_item(t) for t in kwargs["carryover"]])
        else:
            raise InvalidCarryOverType(
                "Carryover should be a string or a list of strings. Not adding carryover to the message."
            )
        return content

    def _process_multimodal_carryover(self, content: List[Dict], kwargs: dict) -> List[Dict]:
        """Prepends the context to a multimodal message."""
        # Makes sure there's a carryover
        if not kwargs.get("carryover"):
            return content

        return [{"type": "text", "text": self._process_carryover("", kwargs)}] + content

    async def a_generate_init_message(self, message: Union[Dict, str, None], **kwargs) -> Union[str, Dict]:
        """Generate the initial message for the agent.
        If message is None, input() will be called to get the initial message.

        Args:
            Please refer to `generate_init_message` for the description of the arguments.

        Returns:
            str or dict: the processed message.
        """
        if message is None:
            message = await self.a_get_human_input(">")

        return self._handle_carryover(message, kwargs)

    def register_function(self, function_map: Dict[str, Union[Callable, None]]):
        """Register functions to the agent.

        Args:
            function_map: a dictionary mapping function names to functions. if function_map[name] is None, the function will be removed from the function_map.
        """
        for name, func in function_map.items():
            self._assert_valid_name(name)
            if func is None and name not in self._function_map.keys():
                warnings.warn(f"The function {name} to remove doesn't exist", name)
            if name in self._function_map:
                warnings.warn(f"Function '{name}' is being overridden.", UserWarning)
        self._function_map.update(function_map)
        self._function_map = {k: v for k, v in self._function_map.items() if v is not None}

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
            if not isinstance(func_sig, dict):
                raise ValueError(
                    f"The function signature must be of the type dict. Received function signature type {type(func_sig)}"
                )

            self._assert_valid_name(func_sig["name"])
            if "functions" in self.llm_config.keys():
                if any(func["name"] == func_sig["name"] for func in self.llm_config["functions"]):
                    warnings.warn(f"Function '{func_sig['name']}' is being overridden.", UserWarning)

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
            if not isinstance(tool_sig, dict):
                raise ValueError(
                    f"The tool signature must be of the type dict. Received tool signature type {type(tool_sig)}"
                )
            self._assert_valid_name(tool_sig["function"]["name"])
            if "tools" in self.llm_config:
                if any(tool["function"]["name"] == tool_sig["function"]["name"] for tool in self.llm_config["tools"]):
                    warnings.warn(f"Function '{tool_sig['function']['name']}' is being overridden.", UserWarning)
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
            if logging_enabled():
                log_function_use(self, func, kwargs, retval)
            return serialize_to_str(retval)

        @load_basemodels_if_needed
        @functools.wraps(func)
        async def _a_wrapped_func(*args, **kwargs):
            retval = await func(*args, **kwargs)
            if logging_enabled():
                log_function_use(self, func, kwargs, retval)
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

    def register_model_client(self, model_client_cls: ModelClient, **kwargs):
        """Register a model client.

        Args:
            model_client_cls: A custom client class that follows the Client interface
            **kwargs: The kwargs for the custom client class to be initialized with
        """
        self.client.register_model_client(model_client_cls, **kwargs)

    def register_hook(self, hookable_method: str, hook: Callable):
        """
        Registers a hook to be called by a hookable method, in order to add a capability to the agent.
        Registered hooks are kept in lists (one per hookable method), and are called in their order of registration.

        Args:
            hookable_method: A hookable method name implemented by ConversableAgent.
            hook: A method implemented by a subclass of AgentCapability.
        """
        assert hookable_method in self.hook_lists, f"{hookable_method} is not a hookable method."
        hook_list = self.hook_lists[hookable_method]
        assert hook not in hook_list, f"{hook} is already registered as a hook."
        hook_list.append(hook)

    def process_all_messages_before_reply(self, messages: List[Dict]) -> List[Dict]:
        """
        Calls any registered capability hooks to process all messages, potentially modifying the messages.
        """
        hook_list = self.hook_lists["process_all_messages_before_reply"]
        # If no hooks are registered, or if there are no messages to process, return the original message list.
        if len(hook_list) == 0 or messages is None:
            return messages

        # Call each hook (in order of registration) to process the messages.
        processed_messages = messages
        for hook in hook_list:
            processed_messages = hook(processed_messages)
        return processed_messages

    def process_last_received_message(self, messages: List[Dict]) -> List[Dict]:
        """
        Calls any registered capability hooks to use and potentially modify the text of the last message,
        as long as the last message is not a function call or exit command.
        """

        # If any required condition is not met, return the original message list.
        hook_list = self.hook_lists["process_last_received_message"]
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

        user_content = last_message["content"]
        if not isinstance(user_content, str) and not isinstance(user_content, list):
            # if the user_content is a string, it is for regular LLM
            # if the user_content is a list, it should follow the multimodal LMM format.
            return messages
        if user_content == "exit":
            return messages  # Last message is an exit command.

        # Call each hook (in order of registration) to process the user's message.
        processed_user_content = user_content
        for hook in hook_list:
            processed_user_content = hook(processed_user_content)

        if processed_user_content == user_content:
            return messages  # No hooks actually modified the user's message.

        # Replace the last user message with the expanded one.
        messages = messages.copy()
        messages[-1]["content"] = processed_user_content
        return messages

    def print_usage_summary(self, mode: Union[str, List[str]] = ["actual", "total"]) -> None:
        """Print the usage summary."""
        iostream = IOStream.get_default()

        if self.client is None:
            iostream.print(f"No cost incurred from agent '{self.name}'.")
        else:
            iostream.print(f"Agent '{self.name}':")
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


def register_function(
    f: Callable[..., Any],
    *,
    caller: ConversableAgent,
    executor: ConversableAgent,
    name: Optional[str] = None,
    description: str,
) -> None:
    """Register a function to be proposed by an agent and executed for an executor.

    This function can be used instead of function decorators `@ConversationAgent.register_for_llm` and
    `@ConversationAgent.register_for_execution`.

    Args:
        f: the function to be registered.
        caller: the agent calling the function, typically an instance of ConversableAgent.
        executor: the agent executing the function, typically an instance of UserProxy.
        name: name of the function. If None, the function name will be used (default: None).
        description: description of the function. The description is used by LLM to decode whether the function
            is called. Make sure the description is properly describing what the function does or it might not be
            called by LLM when needed.

    """
    f = caller.register_for_llm(name=name, description=description)(f)
    executor.register_for_execution(name=name)(f)
