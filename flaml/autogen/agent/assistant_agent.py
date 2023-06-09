from .agent import Agent
from flaml.autogen.code_utils import DEFAULT_MODEL
from flaml import oai


class AssistantAgent(Agent):
    """(Experimental) Assistant agent, able to suggest code blocks."""

    DEFAULT_SYSTEM_MESSAGE = """You are a helpful AI assistant.
    In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute. You must indicate the script type in the code block.
    1. When you need to ask the user for some info, use the code to output the info you need, for example, browse or search the web, download/read a file.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly. Solve the task step by step if you need to.
    If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
    If the result indicates there is an error, fix the error and output the code again. Suggeset the full code instead of partial code or code changes.
    Reply "TERMINATE" in the end when everything is done.
    """

    DEFAULT_CONFIG = {
        "model": DEFAULT_MODEL,
    }

    def __init__(self, name, system_message=DEFAULT_SYSTEM_MESSAGE, **config):
        """
        Args:
            name (str): agent name.
            system_message (str): system message to be sent to the agent.
            **config (dict): other configurations allowed in
              [oai.Completion.create](../oai/Completion#create).
              These configurations will be used when invoking LLM.
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
