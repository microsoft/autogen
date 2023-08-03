from collections import defaultdict
import json
from typing import Callable, Dict, List, Optional, Tuple, Union
from flaml.autogen import oai
from .agent import Agent
from flaml.autogen.code_utils import DEFAULT_MODEL, UNKNOWN, execute_code, extract_code, infer_lang

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


class ResponsiveAgent(Agent):
    """(Experimental) A class for generic responsive agents which can be configured as assistant or user proxy.

    After receiving each message, the agent will send a reply to the sender unless the msg is a termination msg.
    For example, AssistantAgent and UserProxyAgent are subclasses of ResponsiveAgent,
    configured with different default settings.

    To modify auto reply, override `generate_reply` method.
    To disable/enable human response in every turn, set `human_input_mode` to "NEVER" or "ALWAYS".
    To modify the way to get human input, override `get_human_input` method.
    To modify the way to execute code blocks, single code block, or function call, override `execute_code_blocks`,
    `run_code`, and `execute_function` methods respectively.
    To customize the initial message when a conversation starts, override `generate_init_message` method.
    """

    DEFAULT_CONFIG = {
        "model": DEFAULT_MODEL,
    }
    MAX_CONSECUTIVE_AUTO_REPLY = 100  # maximum number of consecutive auto replies (subject to future change)

    def __init__(
        self,
        name: str,
        system_message: Optional[str] = "You are a helpful AI Assistant.",
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Optional[Union[Dict, bool]] = None,
        llm_config: Optional[Union[Dict, bool]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
    ):
        """
        Args:
            name (str): name of the agent.
            system_message (str): system message for the ChatCompletion inference.
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
            function_map (dict[str, callable]): Mapping function names (passed to openai) to callable functions.
            code_execution_config (dict or False): config for the code execution.
                To disable code execution, set to False. Otherwise, set to a dictionary with the following keys:
                - work_dir (Optional, str): The working directory for the code execution.
                    If None, a default working directory will be used.
                    The default working directory is the "extensions" directory under
                    "path_to_flaml/autogen".
                - use_docker (Optional, list, str or bool): The docker image to use for code execution.
                    If a list or a str of image name(s) is provided, the code will be executed in a docker container
                    with the first image successfully pulled.
                    If None, False or empty, the code will be executed in the current environment.
                    Default is True, which will be converted into a list.
                    If the code is executed in the current environment,
                    the code must be trusted.
                - timeout (Optional, int): The maximum execution time in seconds.
            llm_config (dict or False): llm inference configuration.
                Please refer to [autogen.Completion.create](/docs/reference/autogen/oai/completion#create)
                for available options.
                To disable llm-based auto reply, set to False.
            default_auto_reply (str or dict or None): default auto reply when no code execution or llm-based reply is generated.
        """
        super().__init__(name)
        # a dictionary of conversations, default value is list
        self._oai_messages = defaultdict(list)
        self._oai_system_message = [{"content": system_message, "role": "system"}]
        self._is_termination_msg = (
            is_termination_msg if is_termination_msg is not None else (lambda x: x.get("content") == "TERMINATE")
        )
        if llm_config is False:
            self.llm_config = False
        else:
            self.llm_config = self.DEFAULT_CONFIG.copy()
            if isinstance(llm_config, dict):
                self.llm_config.update(llm_config)

        self._code_execution_config = {} if code_execution_config is None else code_execution_config
        self.human_input_mode = human_input_mode
        self._max_consecutive_auto_reply = (
            max_consecutive_auto_reply if max_consecutive_auto_reply is not None else self.MAX_CONSECUTIVE_AUTO_REPLY
        )
        self._consecutive_auto_reply_counter = defaultdict(int)
        self._max_consecutive_auto_reply_dict = defaultdict(self.max_consecutive_auto_reply)
        self._function_map = {} if function_map is None else function_map
        self._default_auto_reply = default_auto_reply
        self._class_specific_reply = []
        self.register_auto_reply(Agent, self._generate_oai_reply)
        self.register_auto_reply(Agent, self._generate_code_execution_reply)
        self.register_auto_reply(Agent, self._generate_function_call_reply)

    def register_auto_reply(self, class_type, reply_func: Callable):
        """Register a class-specific reply function.

        The class-specific reply function will be called when the sender is an instance of the class_type.
        The function registered later will be checked earlier.

        Args:
            class_type (Class): the class type.
            reply_func (Callable): the reply function.
        """
        self._class_specific_reply.append((class_type, reply_func))

    def system_message(self):
        """Return the system message."""
        return self._oai_system_message[0]["content"]

    def update_system_message(self, system_message: str):
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
            self._max_consecutive_auto_reply_dict[sender.name] = value

    def max_consecutive_auto_reply(self, sender: Optional[Agent] = None) -> int:
        """The maximum number of consecutive auto replies."""
        return (
            self._max_consecutive_auto_reply if sender is None else self._max_consecutive_auto_reply_dict[sender.name]
        )

    @property
    def chat_messages(self) -> Dict[str, List[Dict]]:
        """A dictionary of conversations from name to list of ChatCompletion messages."""
        return self._oai_messages

    def last_message(self, agent: Optional[Agent] = None) -> Dict:
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
        return self._oai_messages[agent.name][-1]

    @property
    def use_docker(self) -> Union[bool, str, None]:
        """Bool value of whether to use docker to execute the code,
        or str value of the docker image name to use, or None when code execution is disabled."""
        return None if self._code_execution_config is False else self._code_execution_config.get("use_docker")

    @staticmethod
    def _message_to_dict(message: Union[Dict, str]):
        """Convert a message to a dictionary.

        The message can be a string or a dictionary. The string will be put in the "content" field of the new dictionary.
        """
        if isinstance(message, str):
            return {"content": message}
        else:
            return message

    def _append_oai_message(self, message: Union[Dict, str], role, conversation_id) -> bool:
        """Append a message to the ChatCompletion conversation.

        If the message received is a string, it will be put in the "content" field of the new dictionary.
        If the message received is a dictionary but does not have any of the two fields "content" or "function_call",
            this message is not a valid ChatCompletion message.

        Args:
            message (dict or str): message to be appended to the ChatCompletion conversation.
            role (str): role of the message, can be "assistant" or "function".
            conversation_id (str): id of the conversation, should be the name of the recipient or sender.

        Returns:
            bool: whether the message is appended to the ChatCompletion conversation.
        """
        message = self._message_to_dict(message)
        # create oai message to be appended to the oai conversation that can be passed to oai directly.
        oai_message = {k: message[k] for k in ("content", "function_call", "name", "context") if k in message}
        if "content" not in oai_message and "function_call" not in oai_message:
            return False

        oai_message["role"] = "function" if message.get("role") == "function" else role
        self._oai_messages[conversation_id].append(oai_message)
        return True

    def send(self, message: Union[Dict, str], recipient: Agent):
        """Send a message to another agent.

        Args:
            message (dict or str): message to be sent.
                The message could contain the following fields (either content or function_call must be provided):
                - content (str): the content of the message.
                - function_call (str): the name of the function to be called.
                - name (str): the name of the function to be called.
                - role (str): the role of the message, any role that is not "function"
                    will be modified to "assistant".
                - context (dict): the context of the message, which will be passed to
                    [autogen.Completion.create](../oai/Completion#create).
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

        Raises:
            ValueError: if the message can't be converted into a valid ChatCompletion message.
        """
        # When the agent composes and sends the message, the role of the message is "assistant"
        # unless it's "function".
        valid = self._append_oai_message(message, "assistant", recipient.name)
        if valid:
            recipient.receive(message, self)
        else:
            raise ValueError(
                "Message can't be converted into a valid ChatCompletion message. Either content or function_call must be provided."
            )

    def _print_received_message(self, message: Union[Dict, str], sender: Agent):
        # print the message received
        print(colored(sender.name, "yellow"), "(to", f"{self.name}):\n", flush=True)
        if message.get("role") == "function":
            func_print = f"***** Response from calling function \"{message['name']}\" *****"
            print(colored(func_print, "green"), flush=True)
            print(message["content"], flush=True)
            print(colored("*" * len(func_print), "green"), flush=True)
        else:
            content = message.get("content")
            if content is not None:
                if "context" in message:
                    content = oai.ChatCompletion.instantiate(
                        content,
                        message["context"],
                        self.llm_config and self.llm_config.get("allow_format_str_template", False),
                    )
                print(content, flush=True)
            if "function_call" in message:
                func_print = f"***** Suggested function Call: {message['function_call'].get('name', '(No function name found)')} *****"
                print(colored(func_print, "green"), flush=True)
                print(
                    "Arguments: \n",
                    message["function_call"].get("arguments", "(No arguments found)"),
                    flush=True,
                    sep="",
                )
                print(colored("*" * len(func_print), "green"), flush=True)
        print("\n", "-" * 80, flush=True, sep="")

    def receive(self, message: Union[Dict, str], sender: Agent):
        """Receive a message from another agent.

        Once a message is received, this function sends a reply to the sender or stop.
        The reply can be generated automatically or entered manually by a human.

        Args:
            message (dict or str): message from the sender. If the type is dict, it may contain the following reserved fields (either content or function_call need to be provided).
                1. "content": content of the message, can be None.
                2. "function_call": a dictionary containing the function name and arguments.
                3. "role": role of the message, can be "assistant", "user", "function".
                    This field is only needed to distinguish between "function" or "assistant"/"user".
                4. "name": In most cases, this field is not needed. When the role is "function", this field is needed to indicate the function name.
                5. "context" (dict): the context of the message, which will be passed to
                    [autogen.Completion.create](../oai/Completion#create).
            sender: sender of an Agent instance.

        Raises:
            ValueError: if the message can't be converted into a valid ChatCompletion message.
        """
        message = self._message_to_dict(message)
        # When the agent receives a message, the role of the message is "user". (If 'role' exists and is 'function', it will remain unchanged.)
        valid = self._append_oai_message(message, "user", sender.name)
        if not valid:
            raise ValueError(
                "Received message can't be converted into a valid ChatCompletion message. Either content or function_call must be provided."
            )
        self._print_received_message(message, sender)
        reply = self.generate_reply(sender=sender)
        if reply is not None:
            self.send(reply, sender)

    def initiate_chat(self, recipient: "ResponsiveAgent", clear_history: Optional[bool] = True, **context):
        """Initiate a chat with the recipient agent.

        Reset the consecutive auto reply counter.
        If `clear_history` is True, the chat history with the recipient agent will be cleared.
        `generate_init_message` is called to generate the initial message for the agent.

        Args:
            recipient: the recipient agent.
            clear_history (bool): whether to clear the chat history with the agent.
            **context: any context information.
                "message" needs to be provided if the `generate_init_message` method is not overridden.
        """
        self.reset_consecutive_auto_reply_counter(recipient)
        recipient.reset_consecutive_auto_reply_counter(self)
        if clear_history:
            self.clear_history(recipient)
            recipient.clear_history(self)
        self.send(self.generate_init_message(**context), recipient)

    def reset(self):
        """Reset the agent."""
        self.clear_history()
        self.reset_consecutive_auto_reply_counter()

    def reset_consecutive_auto_reply_counter(self, sender: Optional[Agent] = None):
        """Reset the consecutive_auto_reply_counter of the sender."""
        if sender is None:
            self._consecutive_auto_reply_counter.clear()
        else:
            self._consecutive_auto_reply_counter[sender.name] = 0

    def clear_history(self, agent: Optional[Agent] = None):
        """Clear the chat history of the agent.

        Args:
            agent: the agent with whom the chat history to clear. If None, clear the chat history with all agents.
        """
        if agent is None:
            self._oai_messages.clear()
        else:
            self._oai_messages[agent.name].clear()

    def _generate_oai_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        if self.llm_config is False:
            return False, None
        if messages is None:
            messages = self._oai_messages[sender.name]

        # TODO: #1143 handle token limit exceeded error
        response = oai.ChatCompletion.create(
            context=messages[-1].pop("context", None), messages=self._oai_system_message + messages, **self.llm_config
        )
        return True, oai.ChatCompletion.extract_text_or_function_call(response)[0]

    def _check_termination_and_human_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        if messages is None:
            messages = self._oai_messages[sender.name]
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
            if self._consecutive_auto_reply_counter[sender.name] >= self._max_consecutive_auto_reply_dict[sender.name]:
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
            self._consecutive_auto_reply_counter[sender.name] = 0
            return True, None

        # send the human reply
        if reply or self._max_consecutive_auto_reply_dict[sender.name] == 0:
            # reset the consecutive_auto_reply_counter
            self._consecutive_auto_reply_counter[sender.name] = 0
            return True, reply

        # increment the consecutive_auto_reply_counter
        self._consecutive_auto_reply_counter[sender.name] += 1
        if self.human_input_mode != "NEVER":
            print(colored("\n>>>>>>>> USING AUTO REPLY...", "red"), flush=True)

        return False, None

    def _generate_function_call_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
    ):
        if messages is None:
            messages = self._oai_messages[sender.name]
        message = messages[-1]
        if "function_call" in message:
            _, func_return = self.execute_function(message["function_call"])
            return True, func_return
        return False, None

    def _generate_code_execution_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
    ):
        if self._code_execution_config is False:
            return False, None
        if messages is None:
            messages = self._oai_messages[sender.name]
        message = messages[-1]
        code_blocks = extract_code(message["content"])
        if len(code_blocks) == 1 and code_blocks[0][0] == UNKNOWN:
            # no code block is found, lang should be `UNKNOWN`
            return False, None
            # code_blocks, _ = find_code(messages, sys_msg=self._oai_system_message, **self.llm_config)
            # if len(code_blocks) == 1 and code_blocks[0][0] == UNKNOWN:
            #     return code_blocks[0][1]
        # try to execute the code
        exitcode, logs = self.execute_code_blocks(code_blocks)
        exitcode2str = "execution succeeded" if exitcode == 0 else "execution failed"
        return True, f"exitcode: {exitcode} ({exitcode2str})\nCode output: {logs}"

    def generate_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
    ) -> Union[str, Dict, None]:
        """Reply based on the conversation history.

        First, execute function or code and return the result.
        AI replies are generated only when no code execution is performed.
        Subclasses can override this method to customize the reply.
        Either messages or sender must be provided.

        Args:
            messages: a list of messages in the conversation history.
            default_reply (str or dict): default reply.
            sender: sender of an Agent instance.

        Returns:
            str or dict or None: reply. None if no reply is generated.
        """
        assert messages is not None or sender is not None, "Either messages or sender must be provided."
        final, reply = self._check_termination_and_human_reply(sender=sender)
        if final:
            return reply
        if sender is not None:
            for class_specifc_reply in self._class_specific_reply[-1::-1]:
                if isinstance(sender, class_specifc_reply[0]):
                    final, reply = class_specifc_reply[1](messages, sender)
                    if final:
                        return reply
        return self._default_auto_reply

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
            print(colored(f"\n>>>>>>>> EXECUTING CODE BLOCK {i} (inferred language is {lang})...", "red"), flush=True)
            if lang in ["bash", "shell", "sh"]:
                exitcode, logs, image = self.run_code(code, lang=lang, **self._code_execution_config)
            elif lang in ["python", "Python"]:
                if code.startswith("# filename: "):
                    filename = code[11 : code.find("\n")].strip()
                else:
                    filename = None
                exitcode, logs, image = self.run_code(
                    code,
                    filename=filename,
                    **self._code_execution_config,
                )
            else:
                # In case the language is not supported, we return an error message.
                exitcode, logs, image = 1, f"unknown language {lang}", self._code_execution_config["use_docker"]
                # raise NotImplementedError
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

    def execute_function(self, func_call):
        """Execute a function call and return the result.

        Override this function to modify the way to execute a function call.

        Args:
            func_call: a dictionary extracted from openai message at key "function_call" with keys "name" and "arguments".

        Returns:
            A tuple of (is_exec_success, result_dict).
            is_exec_success (boolean): whether the execution is successful.
            result_dict: a dictionary with keys "name", "role", and "content". Value of "role" is "function".
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
            if arguments:
                print(colored(f"\n>>>>>>>> EXECUTING FUNCTION {func_name}...", "magenta"), flush=True)
                try:
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
        If not overriden, "message" needs to be provided in the context.
        """
        return context["message"]

    def register_function(self, function_map: Dict[str, Callable]):
        """Register functions to the agent.

        Args:
            function_map: a dictionary mapping function names to functions.
        """
        self._function_map.update(function_map)
