from .agent import Agent
from flaml.autogen.code_utils import DEFAULT_MODEL
from flaml import oai


class ChatAgent(Agent):
    DEFAULT_SYSTEM_MESSAGE = """You are a chat agent.
    """

    DEFAULT_CONFIG = {
        "model": DEFAULT_MODEL,
    }

    def __init__(self, name, system_message=DEFAULT_SYSTEM_MESSAGE, **config):
        super().__init__(name, system_message)
        self._config = self.DEFAULT_CONFIG.copy()
        self._config.update(config)
        self._sender_dict = {}

    def receive(self, message, sender):
        super().receive(message, sender)
        responses = oai.ChatCompletion.create(messages=self._conversations[sender.name], **self._config)
        # cost = oai.ChatCompletion.cost(responses)
        response = oai.ChatCompletion.extract_text(responses)[0]
        self._send(response, sender)
