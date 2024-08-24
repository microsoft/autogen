import copy
import sys
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

import tiktoken
from termcolor import colored

from autogen import token_count_utils
from autogen.cache import AbstractCache, Cache
from autogen.types import MessageContentType

from . import transforms_util
from .text_compressors import LLMLingua, TextCompressor


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

    def __init__(self, max_messages: Optional[int] = None, keep_first_message: bool = False):
        """
        Args:
            max_messages Optional[int]: Maximum number of messages to keep in the context. Must be greater than 0 if not None.
            keep_first_message bool: Whether to keep the original first message in the conversation history.
                Defaults to False.
        """
        self._validate_max_messages(max_messages)
        self._max_messages = max_messages
        self._keep_first_message = keep_first_message

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

        if self._max_messages is None or len(messages) <= self._max_messages:
            return messages

        truncated_messages = []
        remaining_count = self._max_messages

        # Start with the first message if we need to keep it
        if self._keep_first_message:
            truncated_messages = [messages[0]]
            remaining_count -= 1

        # Loop through messages in reverse
        for i in range(len(messages) - 1, 0, -1):
            if remaining_count > 1:
                truncated_messages.insert(1 if self._keep_first_message else 0, messages[i])
            if remaining_count == 1:
                # If there's only 1 slot left and it's a 'tools' message, ignore it.
                if messages[i].get("role") != "tool":
                    truncated_messages.insert(1, messages[i])

            remaining_count -= 1
            if remaining_count == 0:
                break

        return truncated_messages

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
        filter_dict: Optional[Dict] = None,
        exclude_filter: bool = True,
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
            filter_dict (None or dict): A dictionary to filter out messages that you want/don't want to compress.
                If None, no filters will be applied.
            exclude_filter (bool): If exclude filter is True (the default value), messages that match the filter will be
                excluded from token truncation. If False, messages that match the filter will be truncated.
        """
        self._model = model
        self._max_tokens_per_message = self._validate_max_tokens(max_tokens_per_message)
        self._max_tokens = self._validate_max_tokens(max_tokens)
        self._min_tokens = self._validate_min_tokens(min_tokens, max_tokens)
        self._filter_dict = filter_dict
        self._exclude_filter = exclude_filter

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
        if not transforms_util.min_tokens_reached(messages, self._min_tokens):
            return messages

        temp_messages = copy.deepcopy(messages)
        processed_messages = []
        processed_messages_tokens = 0

        for msg in reversed(temp_messages):
            # Some messages may not have content.
            if not transforms_util.is_content_right_type(msg.get("content")):
                processed_messages.insert(0, msg)
                continue

            if not transforms_util.should_transform_message(msg, self._filter_dict, self._exclude_filter):
                processed_messages.insert(0, msg)
                processed_messages_tokens += transforms_util.count_text_tokens(msg["content"])
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
            msg_tokens = transforms_util.count_text_tokens(msg["content"])

            # prepend the message to the list to preserve order
            processed_messages_tokens += msg_tokens
            processed_messages.insert(0, msg)

        return processed_messages

    def get_logs(self, pre_transform_messages: List[Dict], post_transform_messages: List[Dict]) -> Tuple[str, bool]:
        pre_transform_messages_tokens = sum(
            transforms_util.count_text_tokens(msg["content"]) for msg in pre_transform_messages if "content" in msg
        )
        post_transform_messages_tokens = sum(
            transforms_util.count_text_tokens(msg["content"]) for msg in post_transform_messages if "content" in msg
        )

        if post_transform_messages_tokens < pre_transform_messages_tokens:
            logs_str = (
                f"Truncated {pre_transform_messages_tokens - post_transform_messages_tokens} tokens. "
                f"Number of tokens reduced from {pre_transform_messages_tokens} to {post_transform_messages_tokens}"
            )
            return logs_str, True
        return "No tokens were truncated.", False

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

    def _validate_min_tokens(self, min_tokens: Optional[int], max_tokens: Optional[int]) -> int:
        if min_tokens is None:
            return 0
        if min_tokens < 0:
            raise ValueError("min_tokens must be None or greater than or equal to 0.")
        if max_tokens is not None and min_tokens > max_tokens:
            raise ValueError("min_tokens must not be more than max_tokens.")
        return min_tokens


class TextMessageCompressor:
    """A transform for compressing text messages in a conversation history.

    It uses a specified text compression method to reduce the token count of messages, which can lead to more efficient
    processing and response generation by downstream models.
    """

    def __init__(
        self,
        text_compressor: Optional[TextCompressor] = None,
        min_tokens: Optional[int] = None,
        compression_params: Dict = dict(),
        cache: Optional[AbstractCache] = Cache.disk(),
        filter_dict: Optional[Dict] = None,
        exclude_filter: bool = True,
    ):
        """
        Args:
            text_compressor (TextCompressor or None): An instance of a class that implements the TextCompressor
                protocol. If None, it defaults to LLMLingua.
            min_tokens (int or None): Minimum number of tokens in messages to apply the transformation. Must be greater
                than or equal to 0 if not None. If None, no threshold-based compression is applied.
            compression_args (dict): A dictionary of arguments for the compression method. Defaults to an empty
                dictionary.
            cache (None or AbstractCache): The cache client to use to store and retrieve previously compressed messages.
                If None, no caching will be used.
            filter_dict (None or dict): A dictionary to filter out messages that you want/don't want to compress.
                If None, no filters will be applied.
            exclude_filter (bool): If exclude filter is True (the default value), messages that match the filter will be
                excluded from compression. If False, messages that match the filter will be compressed.
        """

        if text_compressor is None:
            text_compressor = LLMLingua()

        self._validate_min_tokens(min_tokens)

        self._text_compressor = text_compressor
        self._min_tokens = min_tokens
        self._compression_args = compression_params
        self._filter_dict = filter_dict
        self._exclude_filter = exclude_filter
        self._cache = cache

        # Optimizing savings calculations to optimize log generation
        self._recent_tokens_savings = 0

    def apply_transform(self, messages: List[Dict]) -> List[Dict]:
        """Applies compression to messages in a conversation history based on the specified configuration.

        The function processes each message according to the `compression_args` and `min_tokens` settings, applying
        the specified compression configuration and returning a new list of messages with reduced token counts
        where possible.

        Args:
            messages (List[Dict]): A list of message dictionaries to be compressed.

        Returns:
            List[Dict]: A list of dictionaries with the message content compressed according to the configured
                method and scope.
        """
        # Make sure there is at least one message
        if not messages:
            return messages

        # if the total number of tokens in the messages is less than the min_tokens, return the messages as is
        if not transforms_util.min_tokens_reached(messages, self._min_tokens):
            return messages

        total_savings = 0
        processed_messages = messages.copy()
        for message in processed_messages:
            # Some messages may not have content.
            if not transforms_util.is_content_right_type(message.get("content")):
                continue

            if not transforms_util.should_transform_message(message, self._filter_dict, self._exclude_filter):
                continue

            if transforms_util.is_content_text_empty(message["content"]):
                continue

            cache_key = transforms_util.cache_key(message["content"], self._min_tokens)
            cached_content = transforms_util.cache_content_get(self._cache, cache_key)
            if cached_content is not None:
                message["content"], savings = cached_content
            else:
                message["content"], savings = self._compress(message["content"])

            transforms_util.cache_content_set(self._cache, cache_key, message["content"], savings)

            assert isinstance(savings, int)
            total_savings += savings

        self._recent_tokens_savings = total_savings
        return processed_messages

    def get_logs(self, pre_transform_messages: List[Dict], post_transform_messages: List[Dict]) -> Tuple[str, bool]:
        if self._recent_tokens_savings > 0:
            return f"{self._recent_tokens_savings} tokens saved with text compression.", True
        else:
            return "No tokens saved with text compression.", False

    def _compress(self, content: MessageContentType) -> Tuple[MessageContentType, int]:
        """Compresses the given text or multimodal content using the specified compression method."""
        if isinstance(content, str):
            return self._compress_text(content)
        elif isinstance(content, list):
            return self._compress_multimodal(content)
        else:
            return content, 0

    def _compress_multimodal(self, content: MessageContentType) -> Tuple[MessageContentType, int]:
        tokens_saved = 0
        for item in content:
            if isinstance(item, dict) and "text" in item:
                item["text"], savings = self._compress_text(item["text"])
                tokens_saved += savings

            elif isinstance(item, str):
                item, savings = self._compress_text(item)
                tokens_saved += savings

        return content, tokens_saved

    def _compress_text(self, text: str) -> Tuple[str, int]:
        """Compresses the given text using the specified compression method."""
        compressed_text = self._text_compressor.compress_text(text, **self._compression_args)

        savings = 0
        if "origin_tokens" in compressed_text and "compressed_tokens" in compressed_text:
            savings = compressed_text["origin_tokens"] - compressed_text["compressed_tokens"]

        return compressed_text["compressed_prompt"], savings

    def _validate_min_tokens(self, min_tokens: Optional[int]):
        if min_tokens is not None and min_tokens <= 0:
            raise ValueError("min_tokens must be greater than 0 or None")
