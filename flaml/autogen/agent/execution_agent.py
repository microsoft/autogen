from .agent import Agent
from flaml.autogen.code_utils import execute_code, extract_code


class ExecutionAgent(Agent):
    """(Experimental) Perform actions based on instructions from other agents.
    An execution agent can only communicate with other agents, and perform actions such as executing a command or code.
    """

    def __init__(self, name, system_message="", work_dir=None):
        super().__init__(name, system_message)
        self._word_dir = work_dir

    def receive(self, message, sender):
        super().receive(message, sender)
        # extract code
        code, lang = extract_code(message)
        if lang == "bash":
            assert code.startswith("python ")
            file_name = code[len("python ") :]
            exitcode, logs = execute_code(filename=file_name, work_dir=self._word_dir)
        else:
            exitcode, logs = execute_code(code, work_dir=self._word_dir)
        self._send(f"exitcode: {exitcode}\n{logs.decode('utf-8')}", sender)
