from .agent import Agent
from .execution_agent import ExecutionAgent
from flaml.autogen.code_utils import generate_code, DEFAULT_MODEL
from flaml import oai


class PythonAgent(Agent):
    """(Experimental) Suggest code blocks."""

    DEFAULT_SYSTEM_MESSAGE = """You are a coding agent. You suggest python code for a user to execute for a given task. Don't suggest shell command. Output the code in a coding block. Check the execution result. If the result indicates there is an error, fix the error and output the code again.
    """

    DEFAULT_CONFIG = {
        "model": DEFAULT_MODEL,
    }
    EXECUTION_AGENT_PREFIX = "execution_agent4"
    SUCCESS_EXIT_CODE = "exitcode: 0\n"

    def __init__(self, name, system_message=DEFAULT_SYSTEM_MESSAGE, work_dir=None, **config):
        super().__init__(name, system_message)
        self._work_dir = work_dir
        self._config = self.DEFAULT_CONFIG.copy()
        self._config.update(config)
        self._sender_dict = {}

    def receive(self, message, sender):
        if sender.name not in self._sender_dict:
            self._sender_dict[sender.name] = sender
            self._conversations[sender.name] = [{"content": self._system_message, "role": "system"}]
        super().receive(message, sender)
        if sender.name.startswith(self.EXECUTION_AGENT_PREFIX) and message.startswith(self.SUCCESS_EXIT_CODE):
            # the code is correct, respond to the original sender
            name = sender.name[len(self.EXECUTION_AGENT_PREFIX) :]
            original_sender = self._sender_dict[name]
            output = message[len(self.SUCCESS_EXIT_CODE) :]
            if output:
                self._send(f"{output}", original_sender)
            else:
                self._send("Done. No output.", original_sender)
            return
        responses = oai.ChatCompletion.create(messages=self._conversations[sender.name], **self._config)
        # cost = oai.ChatCompletion.cost(responses)
        response = oai.ChatCompletion.extract_text(responses)[0]
        if sender.name.startswith(self.EXECUTION_AGENT_PREFIX):
            execution_agent = sender
        else:
            # create an execution agent
            execution_agent = ExecutionAgent(f"{self.EXECUTION_AGENT_PREFIX}{sender.name}", work_dir=self._work_dir)
            # initialize the conversation
            self._conversations[execution_agent.name] = self._conversations[sender.name].copy()
            self._sender_dict[execution_agent.name] = execution_agent
        # send the response to the execution agent
        self._send(response, execution_agent)
