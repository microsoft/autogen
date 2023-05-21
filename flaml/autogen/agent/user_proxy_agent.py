from .agent import Agent
from flaml.autogen.code_utils import extract_code, execute_code
from collections import defaultdict


class UserProxyAgent(Agent):
    """(Experimental) A proxy agent for the user, that can execute code and provide feedback to the other agents."""

    MAX_CONSECUTIVE_AUTO_REPLY = 100  # maximum number of consecutive auto replies (subject to future change)

    def __init__(
        self,
        name,
        system_message="",
        work_dir=None,
        human_input_mode="ALWAYS",
        max_consecutive_auto_reply=None,
        is_termination_msg=None,
        use_docker=True,
        **config,
    ):
        """
        Args:
            name (str): name of the agent
            system_message (str): system message to be sent to the agent
            work_dir (str): working directory for the agent
            human_input_mode (bool): whether to ask for human inputs every time a message is received.
                Possible values are "ALWAYS", "TERMINATE", "NEVER".
                (1) When "ALWAYS", the agent prompts for human input every time a message is received.
                    Under this mode, the conversation stops when the human input is "exit",
                    or when is_termination_msg is True and there is no human input.
                (2) When "TERMINATE", the agent only prompts for human input only when a termination message is received or
                    the number of auto reply reaches the max_consecutive_auto_reply.
                (3) When "NEVER", the agent will never prompt for human input. Under this mode, the conversation stops
                    when the number of auto reply reaches the max_consecutive_auto_reply or or when is_termination_msg is True.
            max_consecutive_auto_reply (int): the maximum number of consecutive auto replies.
                default: None (no limit provided, class attribute MAX_CONSECUTIVE_AUTO_REPLY will be used as the limit in this case).
                The limit only plays a role when human_input_mode is not "ALWAYS".
            is_termination_msg (function): a function that takes a message and returns a boolean value.
                This function is used to determine if a received message is a termination message.
            config (dict): other configurations.

        """
        super().__init__(name, system_message)
        self._work_dir = work_dir
        self._human_input_mode = human_input_mode
        self._is_termination_msg = (
            is_termination_msg if is_termination_msg is not None else (lambda x: x == "TERMINATE")
        )
        self._config = config
        self._max_consecutive_auto_reply = (
            max_consecutive_auto_reply if max_consecutive_auto_reply is not None else self.MAX_CONSECUTIVE_AUTO_REPLY
        )
        self._consecutive_auto_reply_counter = defaultdict(int)
        self._use_docker = use_docker

    def _execute_code(self, code, lang):
        """Execute the code and return the result."""
        if lang in ["bash", "shell"]:
            if not code.startswith("python "):
                return 1, f"please do not suggest bash or shell commands like {code}"
            file_name = code[len("python ") :]
            exitcode, logs = execute_code(filename=file_name, work_dir=self._work_dir, use_docker=self._use_docker)
            logs = logs.decode("utf-8")
        elif lang == "python":
            if code.startswith("# filename: "):
                filename = code[11 : code.find("\n")].strip()
            else:
                filename = None
            exitcode, logs = execute_code(code, work_dir=self._work_dir, filename=filename, use_docker=self._use_docker)
            logs = logs.decode("utf-8")
        else:
            # TODO: could this happen?
            exitcode, logs = 1, f"unknown language {lang}"
            # raise NotImplementedError
        return exitcode, logs

    def auto_reply(self, message, sender, default_reply=""):
        """Generate an auto reply."""
        code, lang = extract_code(message)
        if lang == "unknown":
            # no code block is found, lang should be "unknown"
            self._send(default_reply, sender)
        else:
            # try to execute the code
            exitcode, logs = self._execute_code(code, lang)
            exitcode2str = "execution succeeded" if exitcode == 0 else "execution failed"
            self._send(f"exitcode: {exitcode} ({exitcode2str})\nCode output: {logs}", sender)

    def receive(self, message, sender):
        """Receive a message from the sender agent.
        Once a message is received, this function sends a reply to the sender or simply stop.
        The reply can be generated automatically or entered manually by a human.
        """
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
            return
        elif reply:
            # reset the consecutive_auto_reply_counter
            self._consecutive_auto_reply_counter[sender.name] = 0
            self._send(reply, sender)
            return

        self._consecutive_auto_reply_counter[sender.name] += 1
        self.auto_reply(message, sender, default_reply=reply)
