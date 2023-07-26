from collections import defaultdict
import json
from typing import Callable, Dict, List, Optional, Union
from flaml import oai
from .agent import Agent
from flaml.autogen.code_utils import DEFAULT_MODEL, UNKNOWN, execute_code, extract_code, infer_lang


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
        oai_config: Optional[Union[Dict, bool]] = None,
    ):
        """
        Args:
            name (str): name of the agent.
            system_message (str): system message for the oai inference.
            is_termination_msg (function): a function that takes a message in the form of a dictionary
                and returns a boolean value indicating if this received message is a termination message.
                The dict can contain the following keys: "content", "role", "name", "function_call".
            max_consecutive_auto_reply (int): the maximum number of consecutive auto replies.
                default to None (no limit provided, class attribute MAX_CONSECUTIVE_AUTO_REPLY will be used as the limit in this case).
                The limit only plays a role when human_input_mode is not "ALWAYS".
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
            oai_config (dict or False): oai inference configuration.
                Please refer to [oai.Completion.create](/docs/reference/autogen/oai/completion#create)
                for available options.
                To disable oai-based auto reply, set to False.
        """
        super().__init__(name)
        # a dictionary of conversations, default value is list
        self._oai_conversations = defaultdict(list)
        self._system_message = system_message
        self._oai_system_message = [{"content": self._system_message, "role": "system"}]
        self._is_termination_msg = (
            is_termination_msg if is_termination_msg is not None else (lambda x: x.get("content") == "TERMINATE")
        )
        if oai_config is False:
            self.oai_config = False
        else:
            self.oai_config = self.DEFAULT_CONFIG.copy()
            if isinstance(oai_config, dict):
                self.oai_config.update(oai_config)

        self._code_execution_config = {} if code_execution_config is None else code_execution_config
        self.human_input_mode = human_input_mode
        self.max_consecutive_auto_reply = (
            max_consecutive_auto_reply if max_consecutive_auto_reply is not None else self.MAX_CONSECUTIVE_AUTO_REPLY
        )
        self._consecutive_auto_reply_counter = defaultdict(int)
        self._function_map = {} if function_map is None else function_map

    @property
    def oai_conversations(self) -> Dict[str, List[Dict]]:
        """A dictionary of conversations from name to list of oai messages."""
        return self._oai_conversations

    @property
    def use_docker(self) -> Union[bool, str, None]:
        """Bool value of whether to use docker to execute the code,
        or str value of the docker image name to use, or None when code execution is disabled."""
        return None if self._code_execution_config is False else self._code_execution_config.get("use_docker")

    @staticmethod
    def _message_to_dict(message: Union[Dict, str]):
        """Convert a message to a dictionary.

        The message can be a string or a dictionary. The string with be put in the "content" field of the new dictionary.
        """
        if isinstance(message, str):
            return {"content": message}
        else:
            return message

    def _append_oai_message(self, message: Union[Dict, str], role, conversation_id) -> bool:
        """Append a message to the oai conversation.

        If the message received is a string, it will be put in the "content" field of the new dictionary.
        If the message received is a dictionary but does not have any of the two fields "content" or "function_call",
            this message is not a valid oai message and will be ignored.

        Args:
            message (dict or str): message to be appended to the oai conversation.
            role (str): role of the message, can be "assistant" or "function".
            conversation_id (str): id of the conversation, should be the name of the recipient or sender.

        Returns:
            bool: whether the message is appended to the oai conversation.
        """
        message = self._message_to_dict(message)
        # create oai message to be appended to the oai conversation that can be passed to oai directly.
        oai_message = {k: message[k] for k in ("content", "function_call", "name") if k in message}
        if "content" not in oai_message and "function_call" not in oai_message:
            return False

        oai_message["role"] = "function" if message.get("role") == "function" else role
        self._oai_conversations[conversation_id].append(oai_message)
        return True

    def send(self, message: Union[Dict, str], recipient: "Agent"):
        """Send a message to another agent."""
        # When the agent composes and sends the message, the role of the message is "assistant". (If 'role' exists and is 'function', it will remain unchanged.)
        valid = self._append_oai_message(message, "assistant", recipient.name)
        if valid:
            recipient.receive(message, self)

    def _print_received_message(self, message: Union[Dict, str], sender: "Agent"):
        # print the message received
        print(sender.name, "(to", f"{self.name}):\n", flush=True)
        if message.get("role") == "function":
            func_print = f"***** Response from calling function \"{message['name']}\" *****"
            print(func_print, flush=True)
            print(message["content"], flush=True)
            print("*" * len(func_print), flush=True)
        else:
            if message.get("content") is not None:
                print(message["content"], flush=True)
            if "function_call" in message:
                func_print = f"***** Suggested function Call: {message['function_call'].get('name', '(No function name found)')} *****"
                print(func_print, flush=True)
                print(
                    "Arguments: \n",
                    message["function_call"].get("arguments", "(No arguments found)"),
                    flush=True,
                    sep="",
                )
                print("*" * len(func_print), flush=True)
        print("\n", "-" * 80, flush=True, sep="")

    def receive(self, message: Union[Dict, str], sender: "Agent"):
        """Receive a message from another agent.

        Once a message is received, this function sends a reply to the sender or stop.
        The reply can be generated automatically or entered manually by a human.

        Args:
            message (dict or str): message from the sender. If the type is dict, it may contain the following reserved fields (All fields are optional).
                1. "content": content of the message, can be None.
                2. "function_call": a dictionary containing the function name and arguments.
                3. "role": role of the message, can be "assistant", "user", "function".
                    This field is only needed to distinguish between "function" or "assistant"/"user".
                4. "name": In most cases, this field is not needed. When the role is "function", this field is needed to indicate the function name.
            sender: sender of an Agent instance.
        """
        message = self._message_to_dict(message)
        # When the agent receives a message, the role of the message is "user". (If 'role' exists and is 'function', it will remain unchanged.)
        valid = self._append_oai_message(message, "user", sender.name)
        if not valid:
            return
        self._print_received_message(message, sender)

        # default reply is empty (i.e., no reply, in this case we will try to generate auto reply)
        reply = ""
        if self.human_input_mode == "ALWAYS":
            reply = self.get_human_input(
                "Provide feedback to the sender. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "
            )
        elif self._consecutive_auto_reply_counter[
            sender.name
        ] >= self.max_consecutive_auto_reply or self._is_termination_msg(message):
            if self.human_input_mode == "TERMINATE":
                reply = self.get_human_input(
                    "Please give feedback to the sender. (Press enter or type 'exit' to stop the conversation): "
                )
                reply = reply if reply else "exit"
            else:
                # this corresponds to the case when self._human_input_mode == "NEVER"
                reply = "exit"
        if reply == "exit" or (self._is_termination_msg(message) and not reply):
            # reset the consecutive_auto_reply_counter
            self._consecutive_auto_reply_counter[sender.name] = 0
            return
        if reply:
            # reset the consecutive_auto_reply_counter
            self._consecutive_auto_reply_counter[sender.name] = 0
            self.send(reply, sender)
            return

        self._consecutive_auto_reply_counter[sender.name] += 1
        if self.human_input_mode != "NEVER":
            print("\n>>>>>>>> NO HUMAN INPUT RECEIVED. USING AUTO REPLY FOR THE USER...", flush=True)
        self.send(self.generate_reply(self._oai_conversations[sender.name], default_reply=reply), sender)

    def reset(self):
        """Reset the agent."""
        self._oai_conversations.clear()
        self._consecutive_auto_reply_counter.clear()

    def _oai_reply(self, messages: List[Dict]) -> Union[str, Dict]:
        # TODO: #1143 handle token limit exceeded error
        response = oai.ChatCompletion.create(messages=self._oai_system_message + messages, **self.oai_config)
        return oai.ChatCompletion.extract_text_or_function_call(response)[0]

    def generate_reply(self, messages: List[Dict], default_reply: Union[str, Dict] = "") -> Union[str, Dict]:
        """Reply based on the conversation history.

        First, execute function or code and return the result.
        AI replies are generated only when no code execution is performed.
        Subclasses can override this method to customize the reply.

        Args:
            messages: a list of messages in the conversation history.
            default_reply (str or dict): default reply.

        Returns:
            str or dict: reply.
        """
        message = messages[-1]
        if "function_call" in message:
            _, func_return = self.execute_function(message["function_call"])
            return func_return
        if self._code_execution_config is False:
            return default_reply if self.oai_config is False else self._oai_reply(messages)
        code_blocks = extract_code(message["content"])
        if len(code_blocks) == 1 and code_blocks[0][0] == UNKNOWN:
            # no code block is found, lang should be `UNKNOWN`
            return default_reply if self.oai_config is False else self._oai_reply(messages)
        # try to execute the code
        exitcode, logs = self.execute_code_blocks(code_blocks)
        exitcode2str = "execution succeeded" if exitcode == 0 else "execution failed"
        return f"exitcode: {exitcode} ({exitcode2str})\nCode output: {logs}"

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
            logs (bytes): the logs of the code execution.
            image (str or None): the docker image used for the code execution.
        """
        return execute_code(code, **kwargs)

    def execute_code_blocks(self, code_blocks):
        """Execute the code blocks and return the result."""
        logs_all = ""
        for code_block in code_blocks:
            lang, code = code_block
            if not lang:
                lang = infer_lang(code)
            if lang in ["bash", "shell", "sh"]:
                exitcode, logs, image = self.run_code(code, lang=lang, **self._code_execution_config)
                logs = logs.decode("utf-8")
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
                logs = logs.decode("utf-8")
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

    def initiate_chat(self, recipient, **context):
        """Initiate a chat with the recipient agent.

        `generate_init_message` is called to generate the initial message for the agent.

        Args:
            recipient: the recipient agent.
            **context: any context information.
                "message" needs to be provided if the `generate_init_message` method is not overridden.
        """
        self.send(self.generate_init_message(**context), recipient)

    def register_function(self, function_map: Dict[str, Callable]):
        """Register functions to the agent.

        Args:
            function_map: a dictionary mapping function names to functions.
        """
        self._function_map.update(function_map)
