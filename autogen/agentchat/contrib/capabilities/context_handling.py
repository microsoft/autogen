import sys
from termcolor import colored
from typing import Dict, Optional, List
from autogen import ConversableAgent
from autogen import token_count_utils


class TransformChatHistory:
    """
    An agent's chat history with other agents is a common context that it uses to generate a reply.
    This capability allows the agent to transform its chat history prior to using it to generate a reply.
    It does not permanently modify the chat history, but rather processes it on every invocation.

    This capability class enables various strategies to transform chat history, such as:
    - Truncate messages: Truncate each message to first maximum number of tokens.
    - Limit number of messages: Truncate the chat history to a maximum number of (recent) messages.
    - Limit number of tokens: Truncate the chat history to number of recent N messages that fit in
    maximum number of tokens.
    Note that the system message, because of its special significance, is always kept as is.

    The three strategies can be combined. For example, when each of these parameters are specified
    they are used in the following order:
    1. First truncate messages to a maximum number of tokens
    2. Second, it limits the number of message to keep
    3. Third, it limits the total number of tokens in the chat history

    Args:
        max_tokens_per_message (Optional[int]): Maximum number of tokens to keep in each message.
        max_messages (Optional[int]): Maximum number of messages to keep in the context.
        max_tokens (Optional[int]): Maximum number of tokens to keep in the context.
    """

    def __init__(
        self,
        *,
        max_tokens_per_message: Optional[int] = None,
        max_messages: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ):
        self.max_tokens_per_message = max_tokens_per_message if max_tokens_per_message else sys.maxsize
        self.max_messages = max_messages if max_messages else sys.maxsize
        self.max_tokens = max_tokens if max_tokens else sys.maxsize

    def add_to_agent(self, agent: ConversableAgent):
        """
        Adds TransformChatHistory capability to the given agent.
        """
        agent.register_hook(hookable_method=agent.process_all_messages, hook=self._transform_messages)

    def _transform_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Args:
            messages: List of messages to process.

        Returns:
            List of messages with the first system message and the last max_messages messages.
        """
        processed_messages = []
        messages = messages.copy()
        rest_messages = messages

        # check if the first message is a system message and append it to the processed messages
        if len(messages) > 0:
            if messages[0]["role"] == "system":
                msg = messages[0]
                processed_messages.append(msg)
                rest_messages = messages[1:]

        processed_messages_tokens = 0
        for msg in messages:
            msg["content"] = truncate_str_to_tokens(msg["content"], self.max_tokens_per_message)

        # iterate through rest of the messages and append them to the processed messages
        for msg in rest_messages[-self.max_messages :]:
            msg_tokens = token_count_utils.count_token(msg["content"])
            if processed_messages_tokens + msg_tokens > self.max_tokens:
                break
            processed_messages.append(msg)
            processed_messages_tokens += msg_tokens

        total_tokens = 0
        for msg in messages:
            total_tokens += token_count_utils.count_token(msg["content"])

        num_truncated = len(messages) - len(processed_messages)
        if num_truncated > 0 or total_tokens > processed_messages_tokens:
            print(colored(f"Truncated {len(messages) - len(processed_messages)} messages.", "yellow"))
            print(colored(f"Truncated {total_tokens - processed_messages_tokens} tokens.", "yellow"))
        return processed_messages


def truncate_str_to_tokens(text: str, max_tokens: int) -> str:
    """
    Truncate a string so that number of tokens in less than max_tokens.

    Args:
        content: String to process.
        max_tokens: Maximum number of tokens to keep.

    Returns:
        Truncated string.
    """
    truncated_string = ""
    for char in text:
        truncated_string += char
        if token_count_utils.count_token(truncated_string) == max_tokens:
            break
    return truncated_string
