from .agent import Agent
from flaml.autogen.code_utils import UNKNOWN, extract_code, execute_code, infer_lang
from collections import defaultdict
import json
from typing import Callable, Dict, Optional, Union


class UserProxyAgent(Agent):
    """(Experimental) A proxy agent for the user, that can execute code and provide feedback to the other agents."""

    MAX_CONSECUTIVE_AUTO_REPLY = 100  # maximum number of consecutive auto replies (subject to future change)

    def __init__(
        self,
        name: str,
        system_message: Optional[str] = "",
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        human_input_mode: Optional[str] = "ALWAYS",
        function_map: Optional[Dict[str, Callable]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        code_execution_config: Optional[Dict] = None,
        **config,
    ):
        """
        Args:
            name (str): name of the agent.
            system_message (str): system message for the agent.
            is_termination_msg (function): a function that takes a message in the form of a dictionary
                and returns a boolean value indicating if this received message is a termination message.
                The dict can contain the following keys: "content", "role", "name", "function_call".
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
            **config (dict): other configurations.
        """
        super().__init__(name, system_message, is_termination_msg)
        self._code_execution_config = {} if code_execution_config is None else code_execution_config
        self.human_input_mode = human_input_mode
        self.max_consecutive_auto_reply = (
            max_consecutive_auto_reply if max_consecutive_auto_reply is not None else self.MAX_CONSECUTIVE_AUTO_REPLY
        )
        self._consecutive_auto_reply_counter = defaultdict(int)
        self._function_map = {} if function_map is None else function_map

    @property
    def use_docker(self) -> Union[bool, str, None]:
        """bool value of whether to use docker to execute the code,
        or str value of the docker image name to use, or None when code execution is disabled."""
        return None if self._code_execution_config is False else self._code_execution_config.get("use_docker")

    def _run_code(self, code, **kwargs):
        """Run the code and return the result.

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
                exitcode, logs, image = self._run_code(code, lang=lang, **self._code_execution_config)
                logs = logs.decode("utf-8")
            elif lang in ["python", "Python"]:
                if code.startswith("# filename: "):
                    filename = code[11 : code.find("\n")].strip()
                else:
                    filename = None
                exitcode, logs, image = self._run_code(
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

    def auto_reply(self, sender: "Agent", default_reply: Union[str, Dict] = ""):
        """Generate an auto reply."""
        message = self.oai_conversations[sender.name][-1]
        if "function_call" in message:
            _, func_return = self._execute_function(message["function_call"])
            return func_return
        if self._code_execution_config is False:
            return default_reply
        code_blocks = extract_code(message["content"])
        if len(code_blocks) == 1 and code_blocks[0][0] == UNKNOWN:
            # no code block is found, lang should be `UNKNOWN`
            return default_reply
        # try to execute the code
        exitcode, logs = self.execute_code_blocks(code_blocks)
        exitcode2str = "execution succeeded" if exitcode == 0 else "execution failed"
        return f"exitcode: {exitcode} ({exitcode2str})\nCode output: {logs}"

    def receive(self, message: Union[Dict, str], sender):
        """Receive a message from the sender agent.
        Once a message is received, this function sends a reply to the sender or simply stop.
        The reply can be generated automatically or entered manually by a human.
        """
        message = self._message_to_dict(message)
        super().receive(message, sender)
        # default reply is empty (i.e., no reply, in this case we will try to generate auto reply)
        reply = ""
        if self.human_input_mode == "ALWAYS":
            reply = input(
                "Provide feedback to the sender. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "
            )
        elif self._consecutive_auto_reply_counter[
            sender.name
        ] >= self.max_consecutive_auto_reply or self._is_termination_msg(message):
            if self.human_input_mode == "TERMINATE":
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
        no_human_input = "NO HUMAN INPUT RECEIVED. " if self.human_input_mode != "NEVER" else ""
        print(f"\n>>>>>>>> {no_human_input}USING AUTO REPLY FOR THE USER...", flush=True)
        self.send(self.auto_reply(sender, default_reply=reply), sender)

    def reset(self):
        """Reset the agent."""
        super().reset()
        self._consecutive_auto_reply_counter.clear()

    def generate_init_message(self, **context) -> Union[str, Dict]:
        """Generate the initial message for the agent.

        Override this function to customize the initial message based on user's request.
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


class AIUserProxyAgent(UserProxyAgent):
    """(Experimental) A proxy agent for the user, that can execute code and provide feedback to the other agents.

    Compared to UserProxyAgent, this agent can also generate AI replies.
    Code execution is enabled by default. AI replies are generated only when no code execution is performed.
    To disable code execution, set code_execution_config to False.
    """

    def auto_reply(self, sender: "Agent", default_reply: Union[str, Dict] = ""):
        reply = super().auto_reply(sender, default_reply)
        if reply == default_reply:
            # try to generate AI reply
            reply = self._ai_reply(sender)
        return reply
