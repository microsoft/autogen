from .agent import Agent
from flaml.autogen.code_utils import DEFAULT_MODEL
from flaml import oai


class PythonAgent(Agent):
    """(Experimental) Suggest code blocks."""

    DEFAULT_SYSTEM_MESSAGE = """You suggest python code (in a python coding block) for a user to execute for a given task. If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Finish the task smartly. Don't suggest shell command. Don't include multiple code blocks in one response. Use 'print' function for the output when relevant. Check the execution result returned by the user.
    If the result indicates there is an error, fix the error and output the code again.
    Reply "TERMINATE" in the end when the task is done.
    """

    DEFAULT_CONFIG = {
        "model": DEFAULT_MODEL,
    }

    def __init__(self, name, system_message=DEFAULT_SYSTEM_MESSAGE, **config):
        """
        Args:
            name (str): agent name
            system_message (str): system message to be sent to the agent
            config (dict): other configurations.
        """
        super().__init__(name, system_message)
        self._config = self.DEFAULT_CONFIG.copy()
        self._config.update(config)
        self._sender_dict = {}

    def receive(self, message, sender):
        if sender.name not in self._sender_dict:
            self._sender_dict[sender.name] = sender
            self._conversations[sender.name] = [{"content": self._system_message, "role": "system"}]
        super().receive(message, sender)
        responses = oai.ChatCompletion.create(messages=self._conversations[sender.name], **self._config)
        response = oai.ChatCompletion.extract_text(responses)[0]
        self._send(response, sender)

    def reset(self):
        self._sender_dict.clear()
        self._conversations.clear()
