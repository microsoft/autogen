from typing import Callable, Dict, Optional, Union, Tuple, List, Any
from autogen import oai
from autogen import Agent, ConversableAgent

from autogen.token_count_utils import count_token

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


class CompressionAgent(ConversableAgent):
    """(In preview) Assistant agent, designed to solve a task with LLM.

    AssistantAgent is a subclass of ConversableAgent configured with a default system message.
    The default system message is designed to solve a task with LLM,
    including suggesting python code blocks and debugging.
    `human_input_mode` is default to "NEVER"
    and `code_execution_config` is default to False.
    This agent doesn't execute code by default, and expects the user to execute the code.
    """

    #     DEFAULT_SYSTEM_MESSAGE = """You are a helpful AI assistant that will summarize and compress previous messages. The user will input a whole chunk of conversation history. Possible titles include "user", "assistant", "Function Call" and "Function Return".
    # Please follow the rules:
    # 1. You should summarize each of the message and reserve the titles mentioned above. You should also reserve important subtitles and structure within each message, for example, "case", "step" or bullet points.
    # 2. For very short messages, you can choose to not summarize them. For important information like the desription of a problem or task, you should reserve them (if it is not too long).
    # 3. For code snippets, you have two options: 1. reserve the whole exact code snippet. 2. summerize it use this format:
    # CODE: <code type, python, etc>
    # GOAL: <purpose of this code snippet in a short sentence>
    # IMPLEMENTATION: <overall structure of the code>"""

    DEFAULT_SYSTEM_MESSAGE = """You are a helpful AI assistant that will compress messages.
Rules:
1. Please summarize each of the message and reserve the titles: USER, ASSISTANT, FUNCTION_CALL, FUNCTION_RETURN
2. If a message contains code (do not apply when the code is for FUNCTION_CALL), Use indicator "CODE" and summarize what the code is doing with as few words as possible and include details like exact numbers and defined variables.
3. Keep the exact result from code execution or function call. Summarize the result when it returns error or is too long.
"""

    def __init__(
        self,
        name: str = "compressor",
        system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
        llm_config: Optional[Union[Dict, bool]] = None,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "NEVER",
        code_execution_config: Optional[Union[Dict, bool]] = False,
        **kwargs,
    ):
        """
        Args:
            name (str): agent name.
            system_message (str): system message for the ChatCompletion inference.
                Please override this attribute if you want to reprogram the agent.
            llm_config (dict): llm inference configuration.
                Please refer to [Completion.create](/docs/reference/oai/completion#create)
                for available options.
            is_termination_msg (function): a function that takes a message in the form of a dictionary
                and returns a boolean value indicating if this received message is a termination message.
                The dict can contain the following keys: "content", "role", "name", "function_call".
            max_consecutive_auto_reply (int): the maximum number of consecutive auto replies.
                default to None (no limit provided, class attribute MAX_CONSECUTIVE_AUTO_REPLY will be used as the limit in this case).
                The limit only plays a role when human_input_mode is not "ALWAYS".
            **kwargs (dict): Please refer to other kwargs in
                [ConversableAgent](../conversable_agent#__init__).
        """
        super().__init__(
            name,
            system_message,
            is_termination_msg,
            max_consecutive_auto_reply,
            human_input_mode,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            **kwargs,
        )

        self._reply_func_list.clear()
        self.register_reply([Agent, None], CompressionAgent.generate_compressed_reply)

    def generate_compressed_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None, List]]:
        """Compress a list of messages into one message.

        The first message (the initial prompt) will not be compressed.
        The rest of the messages will be compressed into one message, the model is asked to distinuish the role of each message: USER, ASSISTANT, FUNCTION_CALL, FUNCTION_RETURN.
        Check out the DEFAULT_SYSTEM_MESSAGE prompt above.

        TOTHINK: different models have different max_length, right now we will use config passed in, so the model will be the same with the source model.
        If original model is gpt-4; we start compressing at 70% of usage, 70% of 8092 = 5664; and we use gpt 3.5 here max_toke = 4096, it will raise error. choosinng model automatically?
        """
        # Uncomment the following line to check the content to compress
        # print(colored("*" * 30 + "Start compressing the following content:" + "*" * 30, "magenta"), flush=True)

        # 1. use passed-in config and messages
        # in on_oai_limit function function of conversable agent, we will pass in llm_config from "config" parameter.
        llm_config = self.llm_config if config is None else config
        if llm_config is False:
            return False, None
        if messages is None:
            messages = self._oai_messages[sender]

        # 2. stop if there is only one message in the list
        if len(messages) <= 1:
            print(f"Warning: the first message contains {count_token(messages)} tokens, which will not be compressed.")
            return False, None

        # 3. put all history into one, except the first one
        chat_to_compress = "To be compressed:\n"
        for m in messages[1:]:
            if m.get("role") == "function":
                chat_to_compress += f"FUNCTION_RETURN (from \"func_name: {m['name']}\"): \n {m['content']}\n"
            else:
                chat_to_compress += f"{m['role'].upper()}:\n{m['content']}\n"
                if "function_call" in m:
                    chat_to_compress += f"FUNCTION_CALL:\"{m['function_call']}\"\n"

        chat_to_compress = [{"role": "user", "content": chat_to_compress}]
        # Uncomment the following line to check the content to compress
        # print(chat_to_compress[0]["content"])

        # 4. ask LLM to compress
        response = oai.ChatCompletion.create(
            context=None, messages=self._oai_system_message + chat_to_compress, **llm_config
        )
        compressed_message = oai.ChatCompletion.extract_text_or_function_call(response)[0]
        assert isinstance(compressed_message, str), f"compressed_message should be a string: {compressed_message}"

        # 5. add compressed message to the first message and return
        messages = [
            messages[0],
            {"content": "Compressed Content of Previous Chat:\n" + compressed_message, "role": "user"},
        ]
        print(colored("*" * 30 + "Content after compressing:" + "*" * 30, "magenta"), flush=True)
        print(messages[1]["content"], colored("\n" + "*" * 80, "magenta"))
        return True, messages

    def generate_summarized_reply():
        """For all chat history, direct summarize what has been done instead of distingushing agents like userproxy, assistant and functions."""
        pass
