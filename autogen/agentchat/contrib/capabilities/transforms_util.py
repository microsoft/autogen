from typing import Any, Dict, List, Optional, Tuple, Union

from autogen import token_count_utils
from autogen.cache.abstract_cache_base import AbstractCache
from autogen.oai.openai_utils import filter_config
from autogen.types import MessageContentType


def cache_content_get(cache: Optional[AbstractCache], key: str) -> Optional[Tuple[MessageContentType, ...]]:
    if cache:
        cached_value = cache.get(key)
        if cached_value:
            return cached_value


def cache_content_set(cache: Optional[AbstractCache], key: str, content: MessageContentType, *args) -> None:
    if cache:
        cache_value = (content, *args)
        cache.set(key, cache_value)


def min_tokens_reached(messages: List[Dict], min_tokens: Optional[int]) -> bool:
    """Returns True if the total number of tokens in the messages is greater than or equal to the specified value."""
    if not min_tokens:
        return True

    messages_tokens = sum(count_tokens(msg["content"]) for msg in messages if "content" in msg)
    return messages_tokens >= min_tokens


def count_tokens(content: Union[str, List[Dict[str, Any]]]) -> int:
    token_count = 0
    if isinstance(content, str):
        token_count = token_count_utils.count_token(content)
    elif isinstance(content, list):
        for item in content:
            token_count += count_tokens(item.get("text", ""))
    return token_count


def is_content_right_type(content: Any) -> bool:
    return isinstance(content, (str, list))


def is_content_text_empty(content: Union[str, List[Dict[str, Any]]]) -> bool:
    if isinstance(content, str):
        return content == ""
    elif isinstance(content, list):
        return all(is_content_text_empty(item.get("text", "")) for item in content)
    else:
        return False


def should_transform_message(message: Dict[str, Any], filter_dict: Optional[Dict[str, Any]], exclude: bool) -> bool:
    if not filter_dict:
        return True

    return len(filter_config([message], filter_dict, exclude)) > 0
