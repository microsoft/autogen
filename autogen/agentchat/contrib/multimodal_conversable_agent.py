import copy
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from autogen import OpenAIWrapper
from autogen.agentchat import Agent, ConversableAgent
from autogen.img_utils import gpt4v_formatter

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


from autogen.code_utils import content_str

DEFAULT_LMM_SYS_MSG = """You are a helpful AI assistant."""


class MultimodalConversableAgent(ConversableAgent):
    def __init__(
        self,
        name: str,
        system_message: Optional[Union[str, List]] = DEFAULT_LMM_SYS_MSG,
        is_termination_msg: str = None,
        *args,
        **kwargs,
    ):
        """
        Args:
            name (str): agent name.
            system_message (str): system message for the OpenAIWrapper inference.
                Please override this attribute if you want to reprogram the agent.
            **kwargs (dict): Please refer to other kwargs in
                [ConversableAgent](../conversable_agent#__init__).
        """
        super().__init__(
            name,
            system_message,
            is_termination_msg=is_termination_msg,
            *args,
            **kwargs,
        )
        # call the setter to handle special format.
        self.update_system_message(system_message)
        self._is_termination_msg = (
            is_termination_msg
            if is_termination_msg is not None
            else (lambda x: content_str(x.get("content")) == "TERMINATE")
        )

    def update_system_message(self, system_message: Union[Dict, List, str]):
        """Update the system message.

        Args:
            system_message (str): system message for the OpenAIWrapper inference.
        """
        self._oai_system_message[0]["content"] = self._message_to_dict(system_message)["content"]
        self._oai_system_message[0]["role"] = "system"

    @staticmethod
    def _message_to_dict(message: Union[Dict, List, str]) -> Dict:
        """Convert a message to a dictionary. This implementation
        handles the GPT-4V formatting for easier prompts.

        The message can be a string or a dictionary. The string will be put in
        the "content" field of the new dictionary.
        """
        message = copy.deepcopy(message)
        if isinstance(message, str):
            return {"content": gpt4v_formatter(message)}
        if isinstance(message, list):
            return {"content": message}
        if isinstance(message, dict):
            # Ensure the content field is a formatted List rather than str.
            if isinstance(message["content"], str):
                message["content"] = gpt4v_formatter(message["content"])
            return message
        raise ValueError(f"Unsupported message type: {type(message)}")
