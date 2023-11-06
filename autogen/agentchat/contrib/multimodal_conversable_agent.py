from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from autogen import OpenAIWrapper
from autogen.agentchat import Agent, ConversableAgent
from autogen.img_utils import gpt4v_formatter

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


from autogen.code_utils import DEFAULT_MODEL, UNKNOWN, content_str, execute_code, extract_code, infer_lang

DEFAULT_LMM_SYS_MSG = """You are a helpful AI assistant.
You can also view images, where the "<image i>" represent the i-th image you received."""


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

        self.update_system_message(system_message)
        self._is_termination_msg = (
            is_termination_msg
            if is_termination_msg is not None
            else (lambda x: any([item["text"] == "TERMINATE" for item in x.get("content") if item["type"] == "text"]))
        )

    @property
    def system_message(self) -> List:
        """Return the system message."""
        return self._oai_system_message[0]["content"]

    def update_system_message(self, system_message: Union[Dict, List, str]):
        """Update the system message.

        Args:
            system_message (str): system message for the OpenAIWrapper inference.
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

    def _print_received_message(self, message: Union[Dict, str], sender: Agent):
        # print the message received
        print(colored(sender.name, "yellow"), "(to", f"{self.name}):\n", flush=True)
        if message.get("role") == "function":
            func_print = f"***** Response from calling function \"{message['name']}\" *****"
            print(colored(func_print, "green"), flush=True)
            print(content_str(message["content"]), flush=True)
            print(colored("*" * len(func_print), "green"), flush=True)
        else:
            content = message.get("content")
            if content is not None:
                if "context" in message:
                    content = OpenAIWrapper.instantiate(
                        content,
                        message["context"],
                        self.llm_config and self.llm_config.get("allow_format_str_template", False),
                    )
                print(content_str(content), flush=True)
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

    def generate_code_execution_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ):
        """Generate a reply using code execution."""
        code_execution_config = config if config is not None else self._code_execution_config
        if code_execution_config is False:
            return False, None
        if messages is None:
            messages = self._oai_messages[sender]
        last_n_messages = code_execution_config.pop("last_n_messages", 1)

        # iterate through the last n messages reversly
        # if code blocks are found, execute the code blocks and return the output
        # if no code blocks are found, continue
        for i in range(min(len(messages), last_n_messages)):
            message = messages[-(i + 1)]
            if not message["content"]:
                continue
            code_blocks = extract_code(content_str(message["content"]))
            if len(code_blocks) == 1 and code_blocks[0][0] == UNKNOWN:
                continue

            # found code blocks, execute code and push "last_n_messages" back
            exitcode, logs = self.execute_code_blocks(code_blocks)
            code_execution_config["last_n_messages"] = last_n_messages
            exitcode2str = "execution succeeded" if exitcode == 0 else "execution failed"
            return True, f"exitcode: {exitcode} ({exitcode2str})\nCode output: {logs}"

        # no code blocks are found, push last_n_messages back and return.
        code_execution_config["last_n_messages"] = last_n_messages

        return False, None
