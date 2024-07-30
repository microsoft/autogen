import copy
import inspect
import logging
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union
from warnings import warn

from autogen import Agent, ConversableAgent, OpenAIWrapper
from autogen.token_count_utils import count_token, get_max_token_limit, num_tokens_from_functions

from ...formatting_utils import colored

logger = logging.getLogger(__name__)

warn(
    "Context handling with CompressibleAgent is deprecated and will be removed in `0.2.30`. "
    "Please use `TransformMessages`, documentation can be found at https://microsoft.github.io/autogen/docs/topics/handling_long_contexts/intro_to_transform_messages",
    DeprecationWarning,
    stacklevel=2,
)


class CompressibleAgent(ConversableAgent):
    """CompressibleAgent agent. While this agent retains all the default functionalities of the `AssistantAgent`,
    it also provides the added feature of compression when activated through the `compress_config` setting.

    `compress_config` is set to False by default, making this agent equivalent to the `AssistantAgent`.
    This agent does not work well in a GroupChat: The compressed messages will not be sent to all the agents in the group.
    The default system message is the same as AssistantAgent.
    `human_input_mode` is default to "NEVER"
    and `code_execution_config` is default to False.
    This agent doesn't execute code or function call by default.
    """

    DEFAULT_SYSTEM_MESSAGE = """You are a helpful AI assistant.
Solve tasks using your coding and language skills.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
Reply "TERMINATE" in the end when everything is done.
    """
    DEFAULT_COMPRESS_CONFIG = {
        "mode": "TERMINATE",
        "compress_function": None,
        "trigger_count": 0.7,
        "async": False,
        "broadcast": True,
        "verbose": False,
        "leave_last_n": 2,
    }

    def __init__(
        self,
        name: str,
        system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Literal["ALWAYS", "NEVER", "TERMINATE"] = "NEVER",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Optional[Union[Dict, bool]] = False,
        llm_config: Optional[Union[Dict, bool]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        compress_config: Optional[Dict] = False,
        description: Optional[str] = None,
        **kwargs,
    ):
        """
        Args:
            name (str): agent name.
            system_message (str): system message for the ChatCompletion inference.
                Please override this attribute if you want to reprogram the agent.
            llm_config (dict): llm inference configuration.
                Note: you must set `model` in llm_config. It will be used to compute the token count.
                Please refer to [OpenAIWrapper.create](/docs/reference/oai/client#create)
                for available options.
            is_termination_msg (function): a function that takes a message in the form of a dictionary
                and returns a boolean value indicating if this received message is a termination message.
                The dict can contain the following keys: "content", "role", "name", "function_call".
            max_consecutive_auto_reply (int): the maximum number of consecutive auto replies.
                default to None (no limit provided, class attribute MAX_CONSECUTIVE_AUTO_REPLY will be used as the limit in this case).
                The limit only plays a role when human_input_mode is not "ALWAYS".
            compress_config (dict or True/False): config for compression before oai_reply. Default to False.
                You should contain the following keys:
                - "mode" (Optional, str, default to "TERMINATE"): Choose from ["COMPRESS", "TERMINATE", "CUSTOMIZED"].
                    1. `TERMINATE`: terminate the conversation ONLY when token count exceeds the max limit of current model. `trigger_count` is NOT used in this mode.
                    2. `COMPRESS`: compress the messages when the token count exceeds the limit.
                    3. `CUSTOMIZED`: pass in a customized function to compress the messages.
                - "compress_function" (Optional, callable, default to None): Must be provided when mode is "CUSTOMIZED".
                    The function should takes a list of messages and returns a tuple of (is_compress_success: bool, compressed_messages: List[Dict]).
                - "trigger_count" (Optional, float, int, default to 0.7): the threshold to trigger compression.
                    If a float between (0, 1], it is the percentage of token used. if a int, it is the number of tokens used.
                - "async" (Optional, bool, default to False): whether to compress asynchronously.
                - "broadcast" (Optional, bool, default to True): whether to update the compressed message history to sender.
                - "verbose" (Optional, bool, default to False): Whether to print the content before and after compression. Used when mode="COMPRESS".
                - "leave_last_n" (Optional, int, default to 0): If provided, the last n messages will not be compressed. Used when mode="COMPRESS".
            description (str): a short description of the agent. This description is used by other agents
                (e.g. the GroupChatManager) to decide when to call upon this agent. (Default: system_message)
            **kwargs (dict): Please refer to other kwargs in
                [ConversableAgent](../conversable_agent#__init__).
        """
        super().__init__(
            name=name,
            system_message=system_message,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            function_map=function_map,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
            description=description,
            **kwargs,
        )

        self._set_compress_config(compress_config)

        # create a separate client for compression.
        if llm_config is False:
            self.llm_compress_config = False
            self.compress_client = None
        else:
            if "model" not in llm_config:
                raise ValueError("llm_config must contain the 'model' field.")
            self.llm_compress_config = self.llm_config.copy()
            # remove functions
            if "functions" in self.llm_compress_config:
                del self.llm_compress_config["functions"]
            self.compress_client = OpenAIWrapper(**self.llm_compress_config)

        self._reply_func_list.clear()
        self.register_reply([Agent, None], ConversableAgent.generate_oai_reply)
        self.register_reply([Agent], CompressibleAgent.on_oai_token_limit)  # check token limit
        self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_function_call_reply)
        self.register_reply([Agent, None], ConversableAgent.check_termination_and_human_reply)

    def _set_compress_config(self, compress_config: Optional[Dict] = False):
        if compress_config:
            if compress_config is True:
                compress_config = {}
            if not isinstance(compress_config, dict):
                raise ValueError("compress_config must be a dict or True/False.")

            allowed_modes = ["COMPRESS", "TERMINATE", "CUSTOMIZED"]
            if compress_config.get("mode", "TERMINATE") not in allowed_modes:
                raise ValueError(f"Invalid compression mode. Allowed values are: {', '.join(allowed_modes)}")

            self.compress_config = self.DEFAULT_COMPRESS_CONFIG.copy()
            self.compress_config.update(compress_config)

            if not isinstance(self.compress_config["leave_last_n"], int) or self.compress_config["leave_last_n"] < 0:
                raise ValueError("leave_last_n must be a non-negative integer.")

            # convert trigger_count to int, default to 0.7
            trigger_count = self.compress_config["trigger_count"]
            if not (isinstance(trigger_count, int) or isinstance(trigger_count, float)) or trigger_count <= 0:
                raise ValueError("trigger_count must be a positive number.")
            if isinstance(trigger_count, float) and 0 < trigger_count <= 1:
                self.compress_config["trigger_count"] = int(
                    trigger_count * get_max_token_limit(self.llm_config["model"])
                )
                trigger_count = self.compress_config["trigger_count"]
            init_count = self._compute_init_token_count()
            if trigger_count < init_count:
                print(
                    f"Warning: trigger_count {trigger_count} is less than the initial token count {init_count} (system message + function description if passed), compression will be disabled. Please increase trigger_count if you want to enable compression."
                )
                self.compress_config = False

            if self.compress_config["mode"] == "CUSTOMIZED" and self.compress_config["compress_function"] is None:
                raise ValueError("compress_function must be provided when mode is CUSTOMIZED.")
            if self.compress_config["mode"] != "CUSTOMIZED" and self.compress_config["compress_function"] is not None:
                print("Warning: compress_function is provided but mode is not 'CUSTOMIZED'.")

        else:
            self.compress_config = False

    def generate_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        exclude: Optional[List[Callable]] = None,
    ) -> Union[str, Dict, None]:
        """

        Adding to line 202:
        ```
            if messages is not None and messages != self._oai_messages[sender]:
                messages = self._oai_messages[sender]
        ```
        """
        if all((messages is None, sender is None)):
            error_msg = f"Either {messages=} or {sender=} must be provided."
            logger.error(error_msg)
            raise AssertionError(error_msg)

        if messages is None:
            messages = self._oai_messages[sender]

        for reply_func_tuple in self._reply_func_list:
            reply_func = reply_func_tuple["reply_func"]
            if exclude and reply_func in exclude:
                continue
            if inspect.iscoroutinefunction(reply_func):
                continue
            if self._match_trigger(reply_func_tuple["trigger"], sender):
                final, reply = reply_func(self, messages=messages, sender=sender, config=reply_func_tuple["config"])
                if messages is not None and sender is not None and messages != self._oai_messages[sender]:
                    messages = self._oai_messages[sender]
                if final:
                    return reply
        return self._default_auto_reply

    def _compute_init_token_count(self):
        """Check if the agent is LLM-based and compute the initial token count."""
        if self.llm_config is False:
            return 0

        func_count = 0
        if "functions" in self.llm_config:
            func_count = num_tokens_from_functions(self.llm_config["functions"], self.llm_config["model"])

        return func_count + count_token(self._oai_system_message, self.llm_config["model"])

    def _manage_history_on_token_limit(self, messages, token_used, max_token_allowed, model):
        """Manage the message history with different modes when token limit is reached.
        Return:
            final (bool): whether to terminate the agent.
            compressed_messages (List[Dict]): the compressed messages. None if no compression or compression failed.
        """
        # 1. mode = "TERMINATE", terminate the agent if no token left.
        if self.compress_config["mode"] == "TERMINATE":
            if max_token_allowed - token_used <= 0:
                # Terminate if no token left.
                print(
                    colored(
                        f'Warning: Terminate Agent "{self.name}" due to no token left for oai reply. max token for {model}: {max_token_allowed}, existing token count: {token_used}',
                        "yellow",
                    ),
                    flush=True,
                )
                return True, None
            return False, None

        # if token_used is less than trigger_count, no compression will be used.
        if token_used < self.compress_config["trigger_count"]:
            return False, None

        # 2. mode = "COMPRESS" or mode = "CUSTOMIZED", compress the messages
        copied_messages = copy.deepcopy(messages)
        if self.compress_config["mode"] == "COMPRESS":
            _, compress_messages = self.compress_messages(copied_messages)
        elif self.compress_config["mode"] == "CUSTOMIZED":
            _, compress_messages = self.compress_config["compress_function"](copied_messages)
        else:
            raise ValueError(f"Unknown compression mode: {self.compress_config['mode']}")

        if compress_messages is not None:
            for i in range(len(compress_messages)):
                compress_messages[i] = self._get_valid_oai_message(compress_messages[i])
        return False, compress_messages

    def _get_valid_oai_message(self, message):
        """Convert a message into a valid OpenAI ChatCompletion message."""
        oai_message = {k: message[k] for k in ("content", "function_call", "name", "context", "role") if k in message}
        if "content" not in oai_message:
            if "function_call" in oai_message:
                oai_message["content"] = None  # if only function_call is provided, content will be set to None.
            else:
                raise ValueError(
                    "Message can't be converted into a valid ChatCompletion message. Either content or function_call must be provided."
                )
        if "function_call" in oai_message:
            oai_message["role"] = "assistant"  # only messages with role 'assistant' can have a function call.
            oai_message["function_call"] = dict(oai_message["function_call"])
        return oai_message

    def _print_compress_info(self, init_token_count, token_used, token_after_compression):
        to_print = "Token Count (including {} tokens from system msg and function descriptions). Before compression : {} | After: {}".format(
            init_token_count,
            token_used,
            token_after_compression,
        )
        print(colored(to_print, "magenta"), flush=True)
        print("-" * 80, flush=True)

    def on_oai_token_limit(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """(Experimental) Compress previous messages when a threshold of tokens is reached.

        TODO: async compress
        TODO: maintain a list for old oai messages (messages before compression)
        """
        llm_config = self.llm_config if config is None else config
        if self.compress_config is False:
            return False, None
        if messages is None:
            messages = self._oai_messages[sender]

        model = llm_config["model"]
        init_token_count = self._compute_init_token_count()
        token_used = init_token_count + count_token(messages, model)
        final, compressed_messages = self._manage_history_on_token_limit(
            messages, token_used, get_max_token_limit(model), model
        )

        # update message history with compressed messages
        if compressed_messages is not None:
            self._print_compress_info(
                init_token_count, token_used, count_token(compressed_messages, model) + init_token_count
            )
            self._oai_messages[sender] = compressed_messages
            if self.compress_config["broadcast"]:
                # update the compressed message history to sender
                sender._oai_messages[self] = copy.deepcopy(compressed_messages)
                # switching the role of the messages for the sender
                for i in range(len(sender._oai_messages[self])):
                    cmsg = sender._oai_messages[self][i]
                    if "function_call" in cmsg or cmsg["role"] == "user":
                        cmsg["role"] = "assistant"
                    elif cmsg["role"] == "assistant":
                        cmsg["role"] = "user"
                    sender._oai_messages[self][i] = cmsg

            # successfully compressed, return False, None for generate_oai_reply to be called with the updated messages
            return False, None
        return final, None

    def compress_messages(
        self,
        messages: Optional[List[Dict]] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None, List]]:
        """Compress a list of messages into one message.

        The first message (the initial prompt) will not be compressed.
        The rest of the messages will be compressed into one message, the model is asked to distinguish the role of each message: USER, ASSISTANT, FUNCTION_CALL, FUNCTION_RETURN.
        Check out the compress_sys_msg.

        TODO: model used in compression agent is different from assistant agent: For example, if original model used by is gpt-4; we start compressing at 70% of usage, 70% of 8092 = 5664; and we use gpt 3.5 here max_toke = 4096, it will raise error. choosinng model automatically?
        """
        # 1. use the compression client
        client = self.compress_client if config is None else config

        # 2. stop if there is only one message in the list
        leave_last_n = self.compress_config.get("leave_last_n", 0)
        if leave_last_n + 1 >= len(messages):
            logger.warning(
                f"Warning: Compression skipped at trigger count threshold. The first msg and last {leave_last_n} msgs will not be compressed. current msg count: {len(messages)}. Consider raising trigger_count."
            )
            return False, None

        # 3. put all history into one, except the first one
        if self.compress_config["verbose"]:
            print(colored("*" * 30 + "Start compressing the following content:" + "*" * 30, "magenta"), flush=True)

        compressed_prompt = "Below is the compressed content from the previous conversation, evaluate the process and continue if necessary:\n"
        chat_to_compress = "To be compressed:\n"

        for m in messages[1 : len(messages) - leave_last_n]:  # 0, 1, 2, 3, 4
            # Handle function role
            if m.get("role") == "function":
                chat_to_compress += f"##FUNCTION_RETURN## (from function \"{m['name']}\"): \n{m['content']}\n"

            # If name exists in the message
            elif "name" in m:
                chat_to_compress += f"##{m['name']}({m['role'].upper()})## {m['content']}\n"

            # Handle case where content is not None and name is absent
            elif m.get("content"):  # This condition will also handle None and empty string
                if compressed_prompt in m["content"]:
                    chat_to_compress += m["content"].replace(compressed_prompt, "") + "\n"
                else:
                    chat_to_compress += f"##{m['role'].upper()}## {m['content']}\n"

            # Handle function_call in the message
            if "function_call" in m:
                function_name = m["function_call"].get("name")
                function_args = m["function_call"].get("arguments")

                if not function_name or not function_args:
                    chat_to_compress += f"##FUNCTION_CALL## {m['function_call']}\n"
                else:
                    chat_to_compress += f"##FUNCTION_CALL## \nName: {function_name}\nArgs: {function_args}\n"

        chat_to_compress = [{"role": "user", "content": chat_to_compress}]

        if self.compress_config["verbose"]:
            print(chat_to_compress[0]["content"])

        # 4. use LLM to compress
        compress_sys_msg = """You are a helpful assistant that will summarize and compress conversation history.
Rules:
1. Please summarize each of the message and reserve the exact titles: ##USER##, ##ASSISTANT##, ##FUNCTION_CALL##, ##FUNCTION_RETURN##, ##SYSTEM##, ##<Name>(<Title>)## (e.g. ##Bob(ASSISTANT)##).
2. Try to compress the content but reserve important information (a link, a specific number, etc.).
3. Use words to summarize the code blocks or functions calls (##FUNCTION_CALL##) and their goals. For code blocks, please use ##CODE## to mark it.
4. For returns from functions (##FUNCTION_RETURN##) or returns from code execution: summarize the content and indicate the status of the return (e.g. success, error, etc.).
"""
        try:
            response = client.create(
                context=None,
                messages=[{"role": "system", "content": compress_sys_msg}] + chat_to_compress,
            )
        except Exception as e:
            print(colored(f"Failed to compress the content due to {e}", "red"), flush=True)
            return False, None

        compressed_message = self.client.extract_text_or_completion_object(response)[0]
        assert isinstance(compressed_message, str), f"compressed_message should be a string: {compressed_message}"
        if self.compress_config["verbose"]:
            print(
                colored("*" * 30 + "Content after compressing:" + "*" * 30, "magenta"),
                flush=True,
            )
            print(compressed_message, colored("\n" + "*" * 80, "magenta"))

        # 5. add compressed message to the first message and return
        return (
            True,
            [
                messages[0],
                {
                    "content": compressed_prompt + compressed_message,
                    "role": "system",
                },
            ]
            + messages[len(messages) - leave_last_n :],
        )
