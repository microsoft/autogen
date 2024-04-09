#!/usr/bin/env python3 -m pytest

import pytest
from autogen.cache.in_memory_cache import InMemoryCache
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from autogen.experimental.model_clients.openai_client import OpenAI
from autogen.experimental.types import CreateResponse, UserMessage
from conftest import skip_openai  # noqa: E402


@pytest.mark.skipif(skip_openai, reason="openai tests skipped")
@pytest.mark.asyncio
async def test_create() -> None:
    client = OpenAI(model="gpt-3.5-turbo", api_key=os.environ["OPENAI_API_KEY"])
    response = await client.create(messages=[UserMessage("2+2=")])
    assert response.cached is False
    assert response.finish_reason == "stop"
    assert isinstance(response.content, str)


@pytest.mark.skipif(skip_openai, reason="openai tests skipped")
@pytest.mark.asyncio
async def test_tool_calling_extraction() -> None:
    client = OpenAI(model="gpt-3.5-turbo", api_key=os.environ["OPENAI_API_KEY"])
    response = await client.create(
        messages=[
            UserMessage("What is the weather in San Francisco?")
        ],
        extra_create_args={
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "getCurrentWeather",
                        "description": "Get the weather in location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "The city and state e.g. San Francisco, CA",
                                },
                                "unit": {"type": "string", "enum": ["c", "f"]},
                            },
                            "required": ["location"],
                        },
                    },
                }
            ],
        },
    )
    assert response.cached is False
    assert response.finish_reason == "tool_calls"
    assert isinstance(response.content, list)
    response_content = response.content
    assert len(response_content) > 0
    assert response_content[0].name == "getCurrentWeather"


@pytest.mark.skipif(skip_openai, reason="openai tests skipped")
@pytest.mark.asyncio
async def test_cache() -> None:
    client = OpenAI(model="gpt-3.5-turbo", api_key=os.environ["OPENAI_API_KEY"])
    with InMemoryCache(seed="") as cache:
        response = await client.create(messages=[UserMessage("2+2=")], cache=cache)
        assert response.cached is False
        assert response.finish_reason == "stop"
        assert isinstance(response.content, str)
        response_str = response.content
        actual_usage = client.actual_usage()
        total_usage = client.total_usage()

        response = await client.create(messages=[UserMessage("2+2=")], cache=cache)
        assert response.cached is True
        assert response.finish_reason == "stop"
        assert isinstance(response.content, str)
        assert response.content == response_str
        assert client.actual_usage() == actual_usage
        assert client.total_usage().completion_tokens == total_usage.completion_tokens * 2
        assert client.actual_usage().prompt_tokens == actual_usage.prompt_tokens * 2


@pytest.mark.skipif(skip_openai, reason="openai tests skipped")
@pytest.mark.asyncio
async def test_create_stream() -> None:
    client = OpenAI(model="gpt-3.5-turbo", api_key=os.environ["OPENAI_API_KEY"])
    stream = client.create_stream(messages=[UserMessage("2+2=")])
    content = ""
    result = None
    async for chunk in stream:
        if isinstance(chunk, str):
            content += chunk
        else:
            result = chunk

    assert isinstance(result, CreateResponse)
    assert result.cached is False
    assert result.finish_reason == "stop"
    assert isinstance(result.content, str)
    assert content == result.content
