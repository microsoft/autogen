from typing import Any, Dict, Hashable, List, Optional, Tuple

from autogen import token_count_utils
from autogen.cache.abstract_cache_base import AbstractCache
from autogen.oai.openai_utils import filter_config
from autogen.types import MessageContentType


def cache_key(content: MessageContentType, *args: Hashable) -> str:
    """Calculates the cache key for the given message content and any other hashable args.

    Args:
        content (MessageContentType): The message content to calculate the cache key for.
        *args: Any additional hashable args to include in the cache key.
    """
    str_keys = [str(key) for key in (content, *args)]
    return "".join(str_keys)


def cache_content_get(cache: Optional[AbstractCache], key: str) -> Optional[Tuple[MessageContentType, ...]]:
    """Retrieves cachedd content from the cache.

    Args:
        cache (None or AbstractCache): The cache to retrieve the content from. If None, the cache is ignored.
        key (str): The key to retrieve the content from.
    """
    if cache:
        cached_value = cache.get(key)
        if cached_value:
            return cached_value


def cache_content_set(cache: Optional[AbstractCache], key: str, content: MessageContentType, *extra_values):
    """Sets content into the cache.

    Args:
        cache (None or AbstractCache): The cache to set the content into. If None, the cache is ignored.
        key (str): The key to set the content into.
        content (MessageContentType): The message content to set into the cache.
        *extra_values: Additional values to be passed to the cache.
    """
    if cache:
        cache_value = (content, *extra_values)
        cache.set(key, cache_value)


def min_tokens_reached(messages: List[Dict], min_tokens: Optional[int]) -> bool:
    """Returns True if the total number of tokens in the messages is greater than or equal to the specified value.

    Args:
        messages (List[Dict]): A list of messages to check.
    """
    if not min_tokens:
        return True

    messages_tokens = sum(count_text_tokens(msg["content"]) for msg in messages if "content" in msg)
    return messages_tokens >= min_tokens


def count_text_tokens(content: MessageContentType) -> int:
    """Calculates the number of text tokens in the given message content.

    Args:
        content (MessageContentType): The message content to calculate the number of text tokens for.
    """
    token_count = 0
    if isinstance(content, str):
        token_count = token_count_utils.count_token(content)
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                token_count += token_count_utils.count_token(item)
            else:
                token_count += count_text_tokens(item.get("text", ""))
    return token_count


def is_content_right_type(content: Any) -> bool:
    """A helper function to check if the passed in content is of the right type."""
    return isinstance(content, (str, list))


def is_content_text_empty(content: MessageContentType) -> bool:
    """Checks if the content of the message does not contain any text.

    Args:
        content (MessageContentType): The message content to check.
    """
    if isinstance(content, str):
        return content == ""
    elif isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                texts.append(item.get("text", ""))
        return not any(texts)
    else:
        return True


def should_transform_message(message: Dict[str, Any], filter_dict: Optional[Dict[str, Any]], exclude: bool) -> bool:
    """Validates whether the transform should be applied according to the filter dictionary.

    Args:
        message (Dict[str, Any]): The message to validate.
        filter_dict (None or Dict[str, Any]): The filter dictionary to validate against. If None, the transform is always applied.
        exclude (bool): Whether to exclude messages that match the filter dictionary.
    """
    if not filter_dict:
        return True

    return len(filter_config([message], filter_dict, exclude)) > 0
