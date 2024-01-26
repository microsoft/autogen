from __future__ import annotations
import copy
import functools
import inspect
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union


from .. import OpenAIWrapper
from .middleware.base import Middleware
from .middleware.code_execution import CodeExecutionMiddleware
from .middleware.llm import LLMMiddleware
from .middleware.message_store import MessageStoreMiddleware
from .middleware.termination import TerminationAndHumanReplyMiddleware
from .middleware.tool_use import ToolUseMiddleware
from ..cache.cache import Cache


from ..function_utils import get_function_schema, load_basemodels_if_needed, serialize_to_str
from .agent import Agent

__all__ = ("ConversableAgent",)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class _PrintReplyMiddleware:
    """An example of middleware, you can use it as a starting point of implementing your own middleware

    Notice that the `call`` signature must match the function decorated with `register_for_middleware`:
    passing arguments to call() functions must the the same as passing arguments
    to generate_reply() apart from next being passed as a keyword argument
    default values must also be the same
    """

    def __init__(self, agent: Agent):
        self._agent = agent

    def call(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        next: Optional[Callable[..., Any]] = None,
    ) -> Union[str, Dict, None]:
        print(f"generate_reply() called: {sender} sending {messages[-1] if messages else messages}'")
        retval = next(messages, sender)
        return retval

    async def a_call(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        next: Optional[Callable[..., Any]] = None,
    ) -> Union[str, Dict, None]:
        print(f"generate_reply() called: {sender} sending {messages[-1] if messages else messages}'")
        retval = await next(messages, sender)
        return retval


class _ReplyFunctionMiddleware:
    def __init__(
        self,
        recipient: Agent,
        reply_func: Callable[..., Any],
        trigger: Optional[Union[str, type, Agent, Callable[[Agent], bool], List[Any]]],
        config: Optional[Any] = None,
        reset_config: Optional[Callable] = None,
    ):
        if not isinstance(trigger, (type, str, Agent, Callable, list)):
            raise ValueError("trigger must be a class, a string, an agent, a callable or a list.")
        if not callable(reply_func):
            raise ValueError("reply_func must be callable.")
        if not (reset_config is None or callable(reset_config)):
            raise ValueError("reset_config must be callable or None.")
        self._recipient = recipient
        self._trigger = trigger
        self._reply_func = reply_func
        self._config = copy.copy(config)
        self._init_config = config
        self._reset_config = reset_config

    def exclude_on(self, o: Any) -> bool:
        return o == self._reply_func

    def call(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        next: Optional[Callable[..., Any]] = None,
    ) -> Union[str, Dict, None]:
        if self._match_trigger(self._trigger, sender):
            final, reply = self._reply_func(self._recipient, messages, sender, self._config)
            if final:
                # Short-circuit the middleware chain if the reply is final.
                return reply
        return next(messages=messages, sender=sender)

    async def a_call(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        next: Optional[Callable[..., Any]] = None,
    ) -> Union[str, Dict, None]:
        if self._match_trigger(self._trigger, sender):
            if inspect.iscoroutinefunction(self._reply_func):
                final, reply = await self._reply_func(self._recipient, messages, sender, self._config)
                if final:
                    # Short-circuit the middleware chain if the reply is final.
                    return reply
            else:
                raise RuntimeError(
                    "Async reply functions can only be used with ConversableAgent.a_initiate_chat(). "
                    f"The following async reply functions are found: {self._reply_func}"
                )
        return await next(messages=messages, sender=sender)

    def reset_config(self):
        if self._reset_config is not None:
            self._reset_config(self._config)
        else:
            self._config = copy.copy(self._init_config)

    def _match_trigger(
        self,
        trigger: Union[None, str, type, Agent, Callable[[Agent], bool], List],
        sender: Agent,
    ) -> bool:
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
        # print(f"_match_trigger({trigger=}, {sender=})")
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
        self.description = description if description is not None else system_message
        self._default_auto_reply = default_auto_reply
        self._reply_func_list = []
        # TODO: is this still relevant?
        self._ignore_async_func_in_sync_chat_list = []
        self.reply_at_receive = defaultdict(bool)

        # Initialize middleware.
        self._message_store = MessageStoreMiddleware(
            name, allow_format_str_template=llm_config and llm_config.get("allow_format_str_template", False)
        )
        self._llm = LLMMiddleware(name, llm_config, system_message)
        self._tool_use = ToolUseMiddleware(function_map)
        self._code_execution = CodeExecutionMiddleware(code_execution_config)
        self._termination = TerminationAndHumanReplyMiddleware(
            is_termination_msg, max_consecutive_auto_reply, human_input_mode
        )
        self._middleware = [self._termination, self._code_execution, self._tool_use, self._llm]
        self._async_middleware = [self._termination, self._tool_use, self._llm]

        # Middleware lookup for backward compatibility to support the exclude argument in generate_reply.
        self._middleware_lookup = {
            ConversableAgent.generate_oai_reply: self._llm,
            ConversableAgent.generate_code_execution_reply: self._code_execution,
            ConversableAgent.generate_tool_calls_reply: self._tool_use,
            ConversableAgent.generate_function_call_reply: self._tool_use,
            ConversableAgent.check_termination_and_human_reply: self._termination,
        }
        self._async_middleware_lookup = {
            ConversableAgent.a_generate_oai_reply: self._llm,
            ConversableAgent.a_generate_tool_calls_reply: self._tool_use,
            ConversableAgent.a_generate_function_call_reply: self._tool_use,
            ConversableAgent.a_check_termination_and_human_reply: self._termination,
        }

    @property
    def code_execution_config(self) -> Dict:
        """The code execution config."""
        return self._code_execution._code_execution_config

    @code_execution_config.setter
    def code_execution_config(self, value: Dict) -> None:
        """Set the code execution config."""
        self._code_execution._code_execution_config = value

    @property
    def llm_config(self) -> Union[Dict, Literal[False]]:
        """The llm config."""
        return self._llm._llm_config

    @llm_config.setter
    def llm_config(self, value: Union[Dict, Literal[False]]) -> None:
        """Set the llm config."""
        self._llm._llm_config = value

    @property
    def client(self) -> OpenAIWrapper:
        """The OpenAIWrapper instance."""
        return self._llm.client

    @client.setter
    def client(self, value: OpenAIWrapper) -> None:
        """Set the OpenAIWrapper instance."""
        self._llm.client = value

    @property
    def client_cache(self) -> Cache:
        """The Cache instance."""
        return self._llm.client_cache

    @client_cache.setter
    def client_cache(self, value: Cache) -> None:
        """Set the Cache instance."""
        self._llm.client_cache = value

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
        # TODO: wrapper for sync and async reply functions.
        if inspect.iscoroutinefunction(reply_func):
            self._async_middleware.insert(
                position, _ReplyFunctionMiddleware(self, reply_func, trigger, config, reset_config)
            )
            if not ignore_async_in_sync_chat:

                @functools.wraps(reply_func)
                def _raise_runtime_error(*args, **kwargs):
                    raise RuntimeError(
                        "Async reply functions can only be used with ConversableAgent.a_initiate_chat(). "
                        f"The following async reply functions are found: {reply_func.__name__}"
                    )

                self._middleware.insert(
                    position, _ReplyFunctionMiddleware(self, _raise_runtime_error, trigger, config, reset_config)
                )
        else:

            @functools.wraps(reply_func)
            async def _async_reply_func(*args, **kwargs):
                return reply_func(*args, **kwargs)

            self._middleware.insert(position, _ReplyFunctionMiddleware(self, reply_func, trigger, config, reset_config))
            self._async_middleware.insert(
                position, _ReplyFunctionMiddleware(self, _async_reply_func, trigger, config, reset_config)
            )

    @property
    def system_message(self) -> Union[str, List]:
        """Return the system message."""
        return self._llm.system_messages[0]["content"]

    def update_system_message(self, system_message: Union[str, List]):
        """Update the system message.

        Args:
            system_message (str or List): system message for the ChatCompletion inference.
        """
        self._llm.system_messages = system_message

    def update_max_consecutive_auto_reply(self, value: int, sender: Optional[Agent] = None):
        """Update the maximum number of consecutive auto replies.

        Args:
            value (int): the maximum number of consecutive auto replies.
            sender (Agent): when the sender is provided, only update the max_consecutive_auto_reply for that sender.
        """
        self._termination.update_max_consecutive_auto_reply(value, sender)

    def max_consecutive_auto_reply(self, sender: Optional[Agent] = None) -> int:
        """The maximum number of consecutive auto replies."""
        return self._termination.max_consecutive_auto_reply(sender)

    @property
    def chat_messages(self) -> Dict[Agent, List[Dict]]:
        """A dictionary of conversations from agent to list of messages."""
        return self._message_store.oai_messages

    def last_message(self, agent: Optional[Agent] = None) -> Optional[Dict]:
        """The last message exchanged with the agent.

        Args:
            agent (Agent): The agent in the conversation.
                If None and more than one agent's conversations are found, an error will be raised.
                If None and only one conversation is found, the last message of the only conversation will be returned.

        Returns:
            The last message exchanged with the agent.
        """
        return self._message_store.last_message(agent)

    @property
    def use_docker(self) -> Union[bool, str, None]:
        """Bool value of whether to use docker to execute the code,
        or str value of the docker image name to use, or None when code execution is disabled.
        """
        return self._code_execution.use_docker

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
        self._message_store._process_outgoing_message(message, recipient, silent)
        recipient.receive(message, self, request_reply, silent)

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
        self._message_store._process_outgoing_message(message, recipient, silent)
        await recipient.a_receive(message, self, request_reply, silent)

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
        self._message_store._process_incoming_message(message, sender, silent)
        if request_reply is False or request_reply is None and self.reply_at_receive[sender] is False:
            return
        reply = self.generate_reply(messages=self.chat_messages[sender], sender=sender)
        if reply is not None:
            self.send(reply, sender, request_reply=None, silent=silent)

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
        self._message_store._process_incoming_message(message, sender, silent)
        if request_reply is False or request_reply is None and self.reply_at_receive[sender] is False:
            return
        reply = await self.a_generate_reply(sender=sender)
        if reply is not None:
            await self.a_send(reply, sender, request_reply=None, silent=silent)

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
        if self._llm.client is not None:
            self._llm.client.clear_usage_summary()
        for mw in self._middleware:
            if isinstance(mw, _ReplyFunctionMiddleware):
                mw.reset_config()
        for mw in self._async_middleware:
            if isinstance(mw, _ReplyFunctionMiddleware):
                mw.reset_config()

    def stop_reply_at_receive(self, sender: Optional[Agent] = None):
        """Reset the reply_at_receive of the sender."""
        if sender is None:
            self.reply_at_receive.clear()
        else:
            self.reply_at_receive[sender] = False

    def reset_consecutive_auto_reply_counter(self, sender: Optional[Agent] = None):
        """Reset the consecutive_auto_reply_counter of the sender."""
        return self._termination.reset_consecutive_auto_reply_counter(sender)

    def clear_history(self, agent: Optional[Agent] = None):
        """Clear the chat history of the agent.

        Args:
            agent: the agent with whom the chat history to clear. If None, clear the chat history with all agents.
        """
        return self._message_store.clear_history(agent)

    def generate_oai_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate a reply using autogen.oai."""
        if messages is None:
            messages = self.chat_messages[sender]
        return self._llm._generate_oai_reply(messages, config)

    async def a_generate_oai_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate a reply using autogen.oai asynchronously."""
        if messages is None:
            messages = self.chat_messages[sender]
        return await self._llm._a_generate_oai_reply(messages, config)

    def generate_code_execution_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Union[Dict, Literal[False]]] = None,
    ):
        """Generate a reply using code execution."""
        if messages is None:
            messages = self.chat_messages[sender]
        return self._code_execution.call(messages, sender, config=config)

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
        if messages is None:
            messages = self._message_store.oai_messages[sender]
        message = messages[-1]
        return self._tool_use._generate_function_call_reply(message)

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
        if messages is None:
            messages = self.chat_messages[sender]
        message = messages[-1]
        return await self._tool_use._a_generate_function_call_reply(message)

    def generate_tool_calls_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[Dict, None]]:
        """Generate a reply using tool call."""
        if messages is None:
            messages = self.chat_messages[sender]
        message = messages[-1]
        return self._tool_use._generate_tool_calls_reply(message)

    async def a_generate_tool_calls_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[Dict, None]]:
        """Generate a reply using async function call."""
        if messages is None:
            messages = self.chat_messages[sender]
        message = messages[-1]
        return await self._tool_use._a_generate_tool_calls_reply(message)

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
        if messages is None:
            messages = self.chat_messages[sender]
        message = messages[-1]
        return self._termination._check_termination_and_human_reply(message, sender)

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
        if messages is None:
            messages = self.chat_messages[sender]
        message = messages[-1]
        return await self._termination._a_check_termination_and_human_reply(message, sender)

    def _build_middleware_chain(
        self, is_async: bool, exclude: Optional[List[Middleware, Any]] = None
    ) -> Callable[..., Any]:
        def _excluded(mw: Middleware, exclude: List[Any]) -> bool:
            return exclude and (
                (mw in exclude) or (hasattr(mw, "exclude_on") and any(mw.exclude_on(o) for o in exclude))
            )

        if is_async:
            middleware = [mw for mw in self._async_middleware if not _excluded(mw, exclude)]

            # Build middleware chain.
            async def a_chain(messages, sender, next=None):
                return self._default_auto_reply

            # print("Chaining middlewares: ")
            for mw in reversed(middleware):
                # print(f" - {mw}")
                a_chain = functools.partial(mw.a_call, next=a_chain)

            return a_chain

        else:
            middleware = [mw for mw in self._middleware if not _excluded(mw, exclude)]

            # Build middleware chain.
            def chain(messages, sender, next=None):
                return self._default_auto_reply

            # print("Chaining middlewares: ")
            for mw in reversed(middleware):
                # print(f" - {mw}")
                chain = functools.partial(mw.call, next=chain)

            return chain

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
            messages = self.chat_messages[sender]

        chain = self._build_middleware_chain(is_async=False, exclude=exclude)

        # Call the middleware chain.
        return chain(messages=messages, sender=sender)

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
            messages = self.chat_messages[sender]

        chain = self._build_middleware_chain(is_async=True, exclude=exclude)

        # Call the middleware chain.
        return await chain(messages=messages, sender=sender)

    def get_human_input(self, prompt: str) -> str:
        """Get human input.

        Override this method to customize the way to get human input.

        Args:
            prompt (str): prompt for the human input.

        Returns:
            str: human input.
        """
        return self._termination._get_human_input(prompt)

    async def a_get_human_input(self, prompt: str) -> str:
        """(Async) Get human input.

        Override this method to customize the way to get human input.

        Args:
            prompt (str): prompt for the human input.

        Returns:
            str: human input.
        """
        return await self._termination._a_get_human_input(prompt)

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
        return self._code_execution._run_code(code, **kwargs)

    def execute_code_blocks(self, code_blocks):
        """Execute the code blocks and return the result."""
        return self._code_execution._execute_code_blocks(code_blocks)

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
        return self._tool_use._execute_function(func_call, verbose=verbose)

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
        return await self._tool_use._a_execute_function(func_call)

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
        return self._tool_use.register_function(function_map)

    def update_function_signature(self, func_sig: Union[str, Dict], is_remove: None):
        """update a function_signature in the LLM configuration for function_call.

        Args:
            func_sig (str or dict): description/name of the function to update/remove to the model. See: https://platform.openai.com/docs/api-reference/chat/create#chat/create-functions
            is_remove: whether removing the function from llm_config with name 'func_sig'

        Deprecated as of [OpenAI API v1.1.0](https://github.com/openai/openai-python/releases/tag/v1.1.0)
        See https://platform.openai.com/docs/api-reference/chat/create#chat-create-function_call
        """
        return self._llm.update_function_signature(func_sig, is_remove)

    def update_tool_signature(self, tool_sig: Union[str, Dict], is_remove: None):
        """update a tool_signature in the LLM configuration for tool_call.

        Args:
            tool_sig (str or dict): description/name of the tool to update/remove to the model. See: https://platform.openai.com/docs/api-reference/chat/create#chat-create-tools
            is_remove: whether removing the tool from llm_config with name 'tool_sig'
        """
        return self._llm.update_tool_signature(tool_sig, is_remove)

    def can_execute_function(self, name: Union[List[str], str]) -> bool:
        """Whether the agent can execute the function."""
        return self._tool_use.can_execute_function(name)

    @property
    def function_map(self) -> Dict[str, Callable]:
        """Return the function map."""
        return self._tool_use.function_map

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
            if not self.llm_config:
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

    def print_usage_summary(self, mode: Union[str, List[str]] = ["actual", "total"]) -> None:
        """Print the usage summary."""
        return self._llm.print_usage_summary(mode)

    def get_actual_usage(self) -> Union[None, Dict[str, int]]:
        """Get the actual usage summary."""
        return self._llm.get_actual_usage()

    def get_total_usage(self) -> Union[None, Dict[str, int]]:
        """Get the total usage summary."""
        return self._llm.get_total_usage()
