from collections import defaultdict
from typing import Dict, Union


class Agent:
    """(Experimental) An abstract class for AI agent.
    An agent can communicate with other agents and perform actions.
    Different agents can differ in what actions they perform in the `receive` method.

    """

    def __init__(self, name, system_message=""):
        """
        Args:
            name (str): name of the agent
            system_message (str): system message to be sent to the agent
        """
        # empty memory
        self._memory = []
        # a dictionary of conversations, default value is list
        self._oai_conversations = defaultdict(list)
        self._name = name
        self._system_message = system_message

    @property
    def name(self):
        """Get the name of the agent."""
        return self._name

    def _remember(self, memory):
        """Remember something."""
        self._memory.append(memory)

    @staticmethod
    def _message_to_dict(message: Union[Dict, str]):
        """Convert a message to a dictionary.

        The message can be a string or a dictionary. The string with be put in the "content" field of the new dictionary.
        """
        if isinstance(message, str):
            return {"content": message}
        else:
            return message

    def _append_oai_message(self, message: Union[Dict, str], role, conversation_id):
        """Append a message to the openai conversation.

        If the message received is a string, it will be put in the "content" field of the new dictionary.
        If the message received is a dictionary but does not have any of the two fields "content" or "function_call",
            this message is not a valid openai message and will be ignored.

        Args:
            message (dict or str): message to be appended to the openai conversation.
            role (str): role of the message, can be "assistant" or "function".
            conversation_id (str): id of the conversation, should be the name of the recipient or sender.
        """
        message = self._message_to_dict(message)
        # create openai message to be appended to the openai conversation that can be passed to oai directly.
        oai_message = {k: message[k] for k in ("content", "function_call", "name") if k in message}
        if "content" not in oai_message and "function_call" not in oai_message:
            return

        oai_message["role"] = "function" if message.get("role") == "function" else role
        self._oai_conversations[conversation_id].append(oai_message)

    def _send(self, message: Union[Dict, str], recipient):
        """Send a message to another agent."""
        # When the agent composes and sends the message, the role of the message is "assistant". (If 'role' exists and is 'function', it will remain unchanged.)
        self._append_oai_message(message, "assistant", recipient.name)
        recipient.receive(message, self)

    def _receive(self, message: Union[Dict, str], sender):
        """Receive a message from another agent.

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

        # When the agent receives a message, the role of the message is "user". (If 'role' exists and is 'function', it will remain unchanged.)
        self._append_oai_message(message, "user", sender.name)

    def receive(self, message: Union[Dict, str], sender):
        """Receive a message from another agent.
        This method is called by the sender.
        It needs to be overriden by the subclass to perform followup actions.

        Args:
            message (dict or str): message from the sender. If the type is dict, it may contain the following reserved fields (All fields are optional).
                1. "content": content of the message, can be None.
                2. "function_call": a dictionary containing the function name and arguments.
                3. "role": role of the message, can be "assistant", "user", "function".
                    This field is only needed to distinguish between "function" or "assistant"/"user".
                4. "name": In most cases, this field is not needed. When the role is "function", this field is needed to indicate the function name.
            sender: sender of an Agent instance.
        """
        self._receive(message, sender)
        # perform actions based on the message
