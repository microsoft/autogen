from typing import Callable, Dict, List, Optional, Tuple, Union

from autogen import oai
from autogen.agentchat import Agent, ConversableAgent
from autogen.img_utils import gpt4v_formatter

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


DEFAULT_LMM_SYS_MSG = """You are a helpful AI assistant.
You can also view images, where the "<image i>" represent the i-th image you received."""


class MultimodalConversableAgent(ConversableAgent):
    def __init__(
        self,
        name: str,
        system_message: Optional[Tuple[str, List]] = DEFAULT_LMM_SYS_MSG,
        is_termination_msg=None,
        *args,
        **kwargs,
    ):
        """
        Args:
            name (str): agent name.
            system_message (str): system message for the ChatCompletion inference.
                Please override this attribute if you want to reprogram the agent.
            **kwargs (dict): Please refer to other kwargs in
                [ConversableAgent](conversable_agent#__init__).
        """
        super().__init__(
            name,
            system_message,
            is_termination_msg=is_termination_msg,
            *args,
            **kwargs,
        )

        self.update_system_message(system_message)
        self._is_termination_msg = (
            is_termination_msg if is_termination_msg is not None else (lambda x: x.get("content")[-1] == "TERMINATE")
        )

    @property
    def system_message(self) -> List:
        """Return the system message."""
        return self._oai_system_message[0]["content"]

    def update_system_message(self, system_message: Union[Dict, List, str]):
        """Update the system message.

        Args:
            system_message (str): system message for the ChatCompletion inference.
        """
        self._oai_system_message[0]["content"] = self._message_to_dict(system_message)["content"]
        self._oai_system_message[0]["role"] = "system"

    @staticmethod
    def _message_to_dict(message: Union[Dict, List, str]):
        """Convert a message to a dictionary.

        The message can be a string or a dictionary. The string will be put in the "content" field of the new dictionary.
        """
        if isinstance(message, str):
            return {"content": gpt4v_formatter(message)}
        if isinstance(message, list):
            return {"content": message}
        else:
            return message

    def _content_str(self, content: List) -> str:
        rst = ""
        for item in content:
            if isinstance(item, str):
                rst += item
            else:
                assert isinstance(item, dict) and "image" in item, "Wrong content format."
                rst += "<image>"
        return rst

    def _print_received_message(self, message: Union[Dict, str], sender: Agent):
        # print the message received
        print(colored(sender.name, "yellow"), "(to", f"{self.name}):\n", flush=True)
        if message.get("role") == "function":
            func_print = f"***** Response from calling function \"{message['name']}\" *****"
            print(colored(func_print, "green"), flush=True)
            print(self._content_str(message["content"]), flush=True)
            print(colored("*" * len(func_print), "green"), flush=True)
        else:
            content = message.get("content")
            if content is not None:
                if "context" in message:
                    content = oai.ChatCompletion.instantiate(
                        content,
                        message["context"],
                        self.llm_config and self.llm_config.get("allow_format_str_template", False),
                    )
                print(self._content_str(content), flush=True)
            if "function_call" in message:
                func_print = f"***** Suggested function Call: {message['function_call'].get('name', '(No function name found)')} *****"
                print(colored(func_print, "green"), flush=True)
                print(
                    "Arguments: \n",
                    message["function_call"].get("arguments", "(No arguments found)"),
                    flush=True,
                    sep="",
                )
                print(colored("*" * len(func_print), "green"), flush=True)
        print("\n", "-" * 80, flush=True, sep="")

    # TODO: we may want to udpate `generate_code_execution_reply` or `extract_code` for the "content" type change.
