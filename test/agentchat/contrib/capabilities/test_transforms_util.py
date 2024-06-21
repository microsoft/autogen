import itertools
import tempfile
from typing import Dict, Tuple

import pytest

from autogen.agentchat.contrib.capabilities import transforms_util
from autogen.cache.cache import Cache
from autogen.types import MessageContentType

MESSAGES = {
    "message1": {
        "content": [{"text": "Hello"}, {"image_url": {"url": "https://example.com/image.jpg"}}],
        "text_tokens": 1,
    },
    "message2": {"content": [{"image_url": {"url": "https://example.com/image.jpg"}}], "text_tokens": 0},
    "message3": {"content": [{"text": "Hello"}, {"text": "World"}], "text_tokens": 2},
    "message4": {"content": None, "text_tokens": 0},
    "message5": {"content": "Hello there!", "text_tokens": 3},
    "message6": {"content": ["Hello there!", "Hello there!"], "text_tokens": 6},
}


@pytest.mark.parametrize("message", MESSAGES.values())
def test_cache_content(message: Dict[str, MessageContentType]) -> None:
    with tempfile.TemporaryDirectory() as tmpdirname:
        cache = Cache.disk(tmpdirname)
        cache_key_1 = "test_string"

        transforms_util.cache_content_set(cache, cache_key_1, message["content"])
        assert transforms_util.cache_content_get(cache, cache_key_1) == (message["content"],)

        cache_key_2 = "test_list"
        cache_value_2 = [message["content"], 1, "some_string", {"new_key": "new_value"}]
        transforms_util.cache_content_set(cache, cache_key_2, *cache_value_2)
        assert transforms_util.cache_content_get(cache, cache_key_2) == tuple(cache_value_2)
        assert isinstance(cache_value_2[1], int)
        assert isinstance(cache_value_2[2], str)
        assert isinstance(cache_value_2[3], dict)

        cache_key_3 = "test_None"
        transforms_util.cache_content_set(None, cache_key_3, message["content"])
        assert transforms_util.cache_content_get(cache, cache_key_3) is None
        assert transforms_util.cache_content_get(None, cache_key_3) is None


@pytest.mark.parametrize("messages", itertools.product(MESSAGES.values(), MESSAGES.values()))
def test_cache_key(messages: Tuple[Dict[str, MessageContentType], Dict[str, MessageContentType]]) -> None:
    message_1, message_2 = messages
    cache_1 = transforms_util.cache_key(message_1["content"], 10)
    cache_2 = transforms_util.cache_key(message_2["content"], 10)
    if message_1 == message_2:
        assert cache_1 == cache_2
    else:
        assert cache_1 != cache_2


@pytest.mark.parametrize("message", MESSAGES.values())
def test_min_tokens_reached(message: Dict[str, MessageContentType]):
    assert transforms_util.min_tokens_reached([message], None)
    assert transforms_util.min_tokens_reached([message], 0)
    assert not transforms_util.min_tokens_reached([message], message["text_tokens"] + 1)


@pytest.mark.parametrize("message", MESSAGES.values())
def test_count_text_tokens(message: Dict[str, MessageContentType]):
    assert transforms_util.count_text_tokens(message["content"]) == message["text_tokens"]


@pytest.mark.parametrize("message", MESSAGES.values())
def test_is_content_text_empty(message: Dict[str, MessageContentType]):
    assert transforms_util.is_content_text_empty(message["content"]) == (message["text_tokens"] == 0)
