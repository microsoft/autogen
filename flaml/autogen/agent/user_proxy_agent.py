from .agent import Agent
from flaml.autogen.code_utils import UNKNOWN, extract_code, execute_code, infer_lang
from collections import defaultdict
import json
from typing import Callable, Dict, List, Optional, Union


class UserProxyAgent(Agent):
    """(Experimental) A proxy agent for the user, that can execute code and provide feedback to the other agents."""

    MAX_CONSECUTIVE_AUTO_REPLY = 100  # maximum number of consecutive auto replies (subject to future change)

    def __init__(
        self,
        name: str,
        system_message: Optional[str] = "",
        work_dir: Optional[str] = None,
        human_input_mode: Optional[str] = "ALWAYS",
        function_map: Optional[Dict[str, Callable]] = {},
        max_consecutive_auto_reply: Optional[int] = None,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        use_docker: Optional[Union[List[str], str, bool]] = True,
        timeout: Optional[int] = 600,
        **config,
    ):
        """
        Args:
            name (str): name of the agent.
            system_message (str): system message for the agent.
            work_dir (Optional, str): The working directory for the code execution.
                If None, a default working directory will be used.
                The default working directory is the "extensions" directory under
                "path_to_flaml/autogen".
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
            max_consecutive_auto_reply (int): the maximum number of consecutive auto replies.
                default to None (no limit provided, class attribute MAX_CONSECUTIVE_AUTO_REPLY will be used as the limit in this case).
                The limit only plays a role when human_input_mode is not "ALWAYS".
            is_termination_msg (function): a function that takes a message in the form of a dictionary and returns a boolean value indicating if this received message is a termination message.
                The dict can contain the following keys: "content", "role", "name", "function_call".
            use_docker (Optional, list, str or bool): The docker image to use for code execution.
                If a list or a str of image name(s) is provided, the code will be executed in a docker container
                with the first image successfully pulled.
                If None, False or empty, the code will be executed in the current environment.
                Default is True, which will be converted into a list.
                If the code is executed in the current environment,
                the code must be trusted.
            timeout (Optional, int): The maximum execution time in seconds.
            **config (dict): other configurations.
        """
        super().__init__(name, system_message)
        self._work_dir = work_dir
        self._human_input_mode = human_input_mode
        self._is_termination_msg = (
            is_termination_msg if is_termination_msg is not None else (lambda x: x.get("content") == "TERMINATE")
        )
        self._config = config
        self._max_consecutive_auto_reply = (
            max_consecutive_auto_reply if max_consecutive_auto_reply is not None else self.MAX_CONSECUTIVE_AUTO_REPLY
        )
        self._consecutive_auto_reply_counter = defaultdict(int)
        self._use_docker = use_docker
        self._time_out = timeout
        self._function_map = function_map

    @property
    def use_docker(self) -> Union[bool, str]:
        """bool value of whether to use docker to execute the code,
        or str value of the docker image name to use."""
        return self._use_docker

    def execute_code(self, code_blocks):
        """Execute the code and return the result."""
        logs_all = ""
        for code_block in code_blocks:
            lang, code = code_block
            if not lang:
                lang = infer_lang(code)
            if lang in ["bash", "shell", "sh"]:
                exitcode, logs, image = execute_code(
                    code, work_dir=self._work_dir, use_docker=self._use_docker, lang=lang, timeout=self._time_out
                )
                logs = logs.decode("utf-8")
            elif lang in ["python", "Python"]:
                if code.startswith("# filename: "):
                    filename = code[11 : code.find("\n")].strip()
                else:
                    filename = None
                exitcode, logs, image = execute_code(
                    code,
                    work_dir=self._work_dir,
                    filename=filename,
                    use_docker=self._use_docker,
                    timeout=self._time_out,
                )
                logs = logs.decode("utf-8")
            else:
                # In case the language is not supported, we return an error message.
                exitcode, logs, image = 1, f"unknown language {lang}", self._use_docker
                # raise NotImplementedError
            self._use_docker = image
            logs_all += "\n" + logs
            if exitcode != 0:
                return exitcode, logs_all
        return exitcode, logs_all

    @staticmethod
    def _format_json_str(jstr):
        """Remove newlines outside of quotes, and hanlde JSON escape sequences.

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

    def _execute_function(self, func_call):
        """Execute a function call and return the result.

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

    def auto_reply(self, message: dict, sender, default_reply=""):
        """Generate an auto reply."""
        if "function_call" in message:
            _, func_return = self._execute_function(message["function_call"])
            self.send(func_return, sender)
            return

        code_blocks = extract_code(message["content"])
        if len(code_blocks) == 1 and code_blocks[0][0] == UNKNOWN:
            # no code block is found, lang should be `UNKNOWN`
            self.send(default_reply, sender)
        else:
            # try to execute the code
            exitcode, logs = self.execute_code(code_blocks)
            exitcode2str = "execution succeeded" if exitcode == 0 else "execution failed"
            self.send(f"exitcode: {exitcode} ({exitcode2str})\nCode output: {logs}", sender)

    def receive(self, message: Union[Dict, str], sender):
        """Receive a message from the sender agent.
        Once a message is received, this function sends a reply to the sender or simply stop.
        The reply can be generated automatically or entered manually by a human.
        """
        message = self._message_to_dict(message)
        super().receive(message, sender)
        # default reply is empty (i.e., no reply, in this case we will try to generate auto reply)
        reply = ""
        if self._human_input_mode == "ALWAYS":
            reply = input(
                "Provide feedback to the sender. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "
            )
        elif self._consecutive_auto_reply_counter[
            sender.name
        ] >= self._max_consecutive_auto_reply or self._is_termination_msg(message):
            if self._human_input_mode == "TERMINATE":
                reply = input(
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
        print("\n>>>>>>>> NO HUMAN INPUT RECEIVED. USING AUTO REPLY FOR THE USER...", flush=True)
        self.auto_reply(message, sender, default_reply=reply)

    def generate_init_prompt(self, *args, **kwargs) -> Union[str, Dict]:
        """Generate the initial prompt for the agent.

        Override this function to customize the initial prompt based on user's request.
        """
        return args[0]

    def initiate_chat(self, recipient, *args, **kwargs):
        """Initiate a chat with the receiver agent.

        `generate_init_prompt` is called to generate the initial prompt for the agent.

        Args:
            receiver: the receiver agent.
            *args: any additional arguments.
            **kwargs: any additional keyword arguments.
        """
        self.send(self.generate_init_prompt(*args, **kwargs), recipient)

    def register_function(self, function_map: Dict[str, Callable]):
        """Register functions to the agent.

        Args:
            function_map: a dictionary mapping function names to functions.
        """
        self._function_map.update(function_map)
