import copy
import sys
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

import tiktoken
from termcolor import colored

from autogen import token_count_utils


class MessageTransform(Protocol):
    """Defines a contract for message transformation.

    Classes implementing this protocol should provide an `apply_transform` method
    that takes a list of messages and returns the transformed list.
    """

    def apply_transform(self, messages: List[Dict]) -> List[Dict]:
        """Applies a transformation to a list of messages.

        Args:
            messages: A list of dictionaries representing messages.

        Returns:
            A new list of dictionaries containing the transformed messages.
        """
        ...

    def get_logs(self, pre_transform_messages: List[Dict], post_transform_messages: List[Dict]) -> Tuple[str, bool]:
        """Creates the string including the logs of the transformation

        Alongside the string, it returns a boolean indicating whether the transformation had an effect or not.

        Args:
            pre_transform_messages: A list of dictionaries representing messages before the transformation.
            post_transform_messages: A list of dictionaries representig messages after the transformation.

        Returns:
            A tuple with a string with the logs and a flag indicating whether the transformation had an effect or not.
        """
        ...


class MessageHistoryLimiter:
    """Limits the number of messages considered by an agent for response generation.

    This transform keeps only the most recent messages up to the specified maximum number of messages (max_messages).
    It trims the conversation history by removing older messages, retaining only the most recent messages.
    """

    def __init__(self, max_messages: Optional[int] = None):
        """
        Args:
            max_messages Optional[int]: Maximum number of messages to keep in the context. Must be greater than 0 if not None.
        """
        self._validate_max_messages(max_messages)
        self._max_messages = max_messages

    def apply_transform(self, messages: List[Dict]) -> List[Dict]:
        """Truncates the conversation history to the specified maximum number of messages.

        This method returns a new list containing the most recent messages up to the specified
        maximum number of messages (max_messages). If max_messages is None, it returns the
        original list of messages unmodified.

        Args:
            messages (List[Dict]): The list of messages representing the conversation history.

        Returns:
            List[Dict]: A new list containing the most recent messages up to the specified maximum.
        """

        if self._max_messages is None:
            return messages

        return messages[-self._max_messages :]

    def get_logs(self, pre_transform_messages: List[Dict], post_transform_messages: List[Dict]) -> Tuple[str, bool]:
        pre_transform_messages_len = len(pre_transform_messages)
        post_transform_messages_len = len(post_transform_messages)

        if post_transform_messages_len < pre_transform_messages_len:
            logs_str = (
                f"Removed {pre_transform_messages_len - post_transform_messages_len} messages. "
                f"Number of messages reduced from {pre_transform_messages_len} to {post_transform_messages_len}."
            )
            return logs_str, True
        return "No messages were removed.", False

    def _validate_max_messages(self, max_messages: Optional[int]):
        if max_messages is not None and max_messages < 1:
            raise ValueError("max_messages must be None or greater than 1")


class MessageTokenLimiter:
    """Truncates messages to meet token limits for efficient processing and response generation.

    This transformation applies two levels of truncation to the conversation history:

    1. Truncates each individual message to the maximum number of tokens specified by max_tokens_per_message.
    2. Truncates the overall conversation history to the maximum number of tokens specified by max_tokens.

    NOTE: Tokens are counted using the encoder for the specified model. Different models may yield different token
        counts for the same text.

    NOTE: For multimodal LLMs, the token count may be inaccurate as it does not account for the non-text input
        (e.g images).

    The truncation process follows these steps in order:

    1. The minimum tokens threshold (`min_tokens`) is checked (0 by default). If the total number of tokens in messages
        are less than this threshold, then the messages are returned as is. In other case, the following process is applied.
    2. Messages are processed in reverse order (newest to oldest).
    3. Individual messages are truncated based on max_tokens_per_message. For multimodal messages containing both text
        and other types of content, only the text content is truncated.
    4. The overall conversation history is truncated based on the max_tokens limit. Once the accumulated token count
        exceeds this limit, the current message being processed get truncated to meet the total token count and any
        remaining messages get discarded.
    5. The truncated conversation history is reconstructed by prepending the messages to a new list to preserve the
        original message order.
    """

    def __init__(
        self,
        max_tokens_per_message: Optional[int] = None,
        max_tokens: Optional[int] = None,
        min_tokens: Optional[int] = None,
        model: str = "gpt-3.5-turbo-0613",
    ):
        """
        Args:
            max_tokens_per_message (None or int): Maximum number of tokens to keep in each message.
                Must be greater than or equal to 0 if not None.
            max_tokens (Optional[int]): Maximum number of tokens to keep in the chat history.
                Must be greater than or equal to 0 if not None.
            min_tokens (Optional[int]): Minimum number of tokens in messages to apply the transformation.
                Must be greater than or equal to 0 if not None.
            model (str): The target OpenAI model for tokenization alignment.
        """
        self._model = model
        self._max_tokens_per_message = self._validate_max_tokens(max_tokens_per_message)
        self._max_tokens = self._validate_max_tokens(max_tokens)
        self._min_tokens = self._validate_min_tokens(min_tokens, max_tokens)

    def apply_transform(self, messages: List[Dict]) -> List[Dict]:
        """Applies token truncation to the conversation history.

        Args:
            messages (List[Dict]): The list of messages representing the conversation history.

        Returns:
            List[Dict]: A new list containing the truncated messages up to the specified token limits.
        """
        assert self._max_tokens_per_message is not None
        assert self._max_tokens is not None
        assert self._min_tokens is not None

        # if the total number of tokens in the messages is less than the min_tokens, return the messages as is
        if not self._are_min_tokens_reached(messages):
            return messages

        temp_messages = copy.deepcopy(messages)
        processed_messages = []
        processed_messages_tokens = 0

        for msg in reversed(temp_messages):
            # Some messages may not have content.
            if not isinstance(msg.get("content"), (str, list)):
                processed_messages.insert(0, msg)
                continue

            expected_tokens_remained = self._max_tokens - processed_messages_tokens - self._max_tokens_per_message

            # If adding this message would exceed the token limit, truncate the last message to meet the total token
            # limit and discard all remaining messages
            if expected_tokens_remained < 0:
                msg["content"] = self._truncate_str_to_tokens(
                    msg["content"], self._max_tokens - processed_messages_tokens
                )
                processed_messages.insert(0, msg)
                break

            msg["content"] = self._truncate_str_to_tokens(msg["content"], self._max_tokens_per_message)
            msg_tokens = _count_tokens(msg["content"])

            # prepend the message to the list to preserve order
            processed_messages_tokens += msg_tokens
            processed_messages.insert(0, msg)

        return processed_messages

    def get_logs(self, pre_transform_messages: List[Dict], post_transform_messages: List[Dict]) -> Tuple[str, bool]:
        pre_transform_messages_tokens = sum(
            _count_tokens(msg["content"]) for msg in pre_transform_messages if "content" in msg
        )
        post_transform_messages_tokens = sum(
            _count_tokens(msg["content"]) for msg in post_transform_messages if "content" in msg
        )

        if post_transform_messages_tokens < pre_transform_messages_tokens:
            logs_str = (
                f"Truncated {pre_transform_messages_tokens - post_transform_messages_tokens} tokens. "
                f"Number of tokens reduced from {pre_transform_messages_tokens} to {post_transform_messages_tokens}"
            )
            return logs_str, True
        return "No tokens were truncated.", False

    def _are_min_tokens_reached(self, messages: List[Dict]) -> bool:
        """
        Returns True if no minimum tokens restrictions are applied.

        Either if the total number of tokens in the messages is greater than or equal to the `min_theshold_tokens`,
        or no minimum tokens threshold is set.
        """
        if not self._min_tokens:
            return True

        messages_tokens = sum(_count_tokens(msg["content"]) for msg in messages if "content" in msg)
        return messages_tokens >= self._min_tokens

    def _truncate_str_to_tokens(self, contents: Union[str, List], n_tokens: int) -> Union[str, List]:
        if isinstance(contents, str):
            return self._truncate_tokens(contents, n_tokens)
        elif isinstance(contents, list):
            return self._truncate_multimodal_text(contents, n_tokens)
        else:
            raise ValueError(f"Contents must be a string or a list of dictionaries. Received type: {type(contents)}")

    def _truncate_multimodal_text(self, contents: List[Dict[str, Any]], n_tokens: int) -> List[Dict[str, Any]]:
        """Truncates text content within a list of multimodal elements, preserving the overall structure."""
        tmp_contents = []
        for content in contents:
            if content["type"] == "text":
                truncated_text = self._truncate_tokens(content["text"], n_tokens)
                tmp_contents.append({"type": "text", "text": truncated_text})
            else:
                tmp_contents.append(content)
        return tmp_contents

    def _truncate_tokens(self, text: str, n_tokens: int) -> str:
        encoding = tiktoken.encoding_for_model(self._model)  # Get the appropriate tokenizer

        encoded_tokens = encoding.encode(text)
        truncated_tokens = encoded_tokens[:n_tokens]
        truncated_text = encoding.decode(truncated_tokens)  # Decode back to text

        return truncated_text

    def _validate_max_tokens(self, max_tokens: Optional[int] = None) -> Optional[int]:
        if max_tokens is not None and max_tokens < 0:
            raise ValueError("max_tokens and max_tokens_per_message must be None or greater than or equal to 0")

        try:
            allowed_tokens = token_count_utils.get_max_token_limit(self._model)
        except Exception:
            print(colored(f"Model {self._model} not found in token_count_utils.", "yellow"))
            allowed_tokens = None

        if max_tokens is not None and allowed_tokens is not None:
            if max_tokens > allowed_tokens:
                print(
                    colored(
                        f"Max token was set to {max_tokens}, but {self._model} can only accept {allowed_tokens} tokens. Capping it to {allowed_tokens}.",
                        "yellow",
                    )
                )
                return allowed_tokens

        return max_tokens if max_tokens is not None else sys.maxsize

    def _validate_min_tokens(self, min_tokens: int, max_tokens: int) -> int:
        if min_tokens is None:
            return 0
        if min_tokens < 0:
            raise ValueError("min_tokens must be None or greater than or equal to 0.")
        if max_tokens is not None and min_tokens > max_tokens:
            raise ValueError("min_tokens must not be more than max_tokens.")
        return min_tokens


def _count_tokens(content: Union[str, List[Dict[str, Any]]]) -> int:
    token_count = 0
    if isinstance(content, str):
        token_count = token_count_utils.count_token(content)
    elif isinstance(content, list):
        for item in content:
            token_count += _count_tokens(item.get("text", ""))
    return token_count
