import sys
from typing import Dict, List, Optional, Protocol

import tiktoken
from termcolor import colored

from autogen import ConversableAgent, token_count_utils


class MessageTransform(Protocol):
    def apply(self, messages: List[Dict]) -> List[Dict]:
        ...


class TransformMessages:
    def __init__(self, *, transforms: List[MessageTransform] = []):
        self._transforms = transforms

    def add_to_agent(self, agent: ConversableAgent):
        agent.register_hook(
            hookable_method="process_all_messages_before_reply",
            hook=self._transform_messages,
        )

    def _transform_messages(self, messages: List[Dict]) -> List[Dict]:
        temp_messages = messages.copy()
        system_message = None

        if messages[0]["role"] == "system":
            system_message = messages[0].copy()
            temp_messages.pop(0)

        for transform in self._transforms:
            temp_messages = transform.apply(temp_messages)

        if system_message:
            temp_messages.insert(0, system_message)

        return temp_messages


class MaxMessagesTransform:
    def __init__(self, max_messages: Optional[int] = None):
        self._validate_max_messages(max_messages)
        self._max_messages = max_messages if max_messages else sys.maxsize

    def apply(self, messages: List[Dict]) -> List[Dict]:
        if self._max_messages is None:
            return messages

        return messages[-self._max_messages :]

    def _validate_max_messages(self, max_messages: Optional[int]):
        if max_messages is not None and max_messages < 1:
            raise ValueError("max_messages must be None or greater than 1")


class TruncateMessageTransform:
    def __init__(
        self,
        max_tokens_per_message: Optional[int] = None,
        max_tokens: Optional[int] = None,
        model: str = "gpt-3.5-turbo-0613",
    ):
        self._validate_max_tokens(max_tokens_per_message)

        self._max_tokens_per_message = max_tokens_per_message if max_tokens_per_message else sys.maxsize
        self._max_tokens = max_tokens if max_tokens else sys.maxsize
        self._model = model

    def apply(self, messages: List[Dict]) -> List[Dict]:
        assert self._max_tokens_per_message is not None
        assert self._max_tokens is not None

        temp_messages = messages.copy()
        processed_messages = []
        processed_messages_tokens = 0

        # calculate tokens for all messages
        total_tokens = sum(token_count_utils.count_token(msg["content"]) for msg in temp_messages)

        for msg in reversed(temp_messages):
            msg["content"] = truncate_str_to_tokens(msg["content"], self._max_tokens_per_message, model=self._model)
            msg_tokens = token_count_utils.count_token(msg["content"])

            if processed_messages_tokens + msg_tokens > self._max_tokens:
                break

            # append the message to the beginning of the list to preserve order
            processed_messages_tokens += msg_tokens
            processed_messages.insert(0, msg)

        if total_tokens > processed_messages_tokens:
            print(
                colored(
                    f"Truncated {total_tokens - processed_messages_tokens} tokens. Tokens reduced from {total_tokens} to {processed_messages_tokens}",
                    "yellow",
                )
            )

        return processed_messages

    def _validate_max_tokens(self, max_tokens: Optional[int] = None):
        if max_tokens is not None and max_tokens < 1:
            raise ValueError("max_tokens_per_message must be None or greater than 1")


def truncate_str_to_tokens(text: str, max_tokens: int, model: str = "gpt-3.5-turbo-0613") -> str:
    """Truncate a string so that the number of tokens is less than or equal to max_tokens using tiktoken.

    Args:
        text: The string to truncate.
        max_tokens: The maximum number of tokens to keep.
        model: The target OpenAI model for tokenization alignment.

    Returns:
        The truncated string.
    """

    encoding = tiktoken.encoding_for_model(model)  # Get the appropriate tokenizer

    encoded_tokens = encoding.encode(text)
    truncated_tokens = encoded_tokens[:max_tokens]
    truncated_text = encoding.decode(truncated_tokens)  # Decode back to text

    return truncated_text
