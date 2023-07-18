from .agent import Agent
from flaml.autogen.code_utils import DEFAULT_MODEL
from flaml import oai
from typing import Dict, Union


class AssistantAgent(Agent):
    """(Experimental) Assistant agent, able to suggest code blocks with default system message."""

    DEFAULT_SYSTEM_MESSAGE = """You are a helpful AI assistant.
    In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute. You must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly. Solve the task step by step if you need to.
    If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
    If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
    When you find an answer, verify the answer carefully. If a function for planning is provided, call the function to make plans and verify the execution.
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

    def receive(self, message: Union[Dict, str], sender):
        if sender.name not in self._sender_dict:
            self._sender_dict[sender.name] = sender
            self._oai_conversations[sender.name] = [{"content": self._system_message, "role": "system"}]

        super().receive(message, sender)
        responses = oai.ChatCompletion.create(messages=self._oai_conversations[sender.name], **self._config)
        self.send(oai.ChatCompletion.extract_text_or_function_call(responses)[0], sender)

    def reset(self):
        self._sender_dict.clear()
        self._oai_conversations.clear()
