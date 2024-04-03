#!/usr/bin/env python3 -m pytest

import pytest
from autogen import config_list_from_json
from autogen.cache.in_memory_cache import InMemoryCache
from autogen.experimental.model_client.factory import DEFAULT_FACTORY
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402

OAI_CONFIG_LIST = "OAI_CONFIG_LIST"


@pytest.mark.skipif(skip_openai, reason="openai tests skipped")
@pytest.mark.asyncio
async def test_create() -> None:
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        filter_dict={"api_type": ["azure"], "model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    client = DEFAULT_FACTORY.create_from_config(
        {
            "config_list": config_list,
        }
    )
    response = await client.create(messages=[{"role": "user", "content": "2+2="}])
    assert response["cached"] is False
    assert response["finish_reason"] == "stop"
    assert isinstance(response["content"], str)


@pytest.mark.skipif(skip_openai, reason="openai tests skipped")
@pytest.mark.asyncio
async def test_tool_calling_extraction() -> None:
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        filter_dict={"api_type": ["azure"], "model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    client = DEFAULT_FACTORY.create_from_config(
        {
            "config_list": config_list,
        }
    )

    response = await client.create(
        messages=[
            {
                "role": "user",
                "content": "What is the weather in San Francisco?",
            },
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
    assert response["cached"] is False
    assert response["finish_reason"] == "tool_calls"
    assert isinstance(response["content"], list)
    response_content = response["content"]
    assert len(response_content) > 0
    assert response_content[0]["function"]["name"] == "getCurrentWeather"


@pytest.mark.skipif(skip_openai, reason="openai tests skipped")
@pytest.mark.asyncio
async def test_cache() -> None:
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        filter_dict={"api_type": ["azure"], "model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    client = DEFAULT_FACTORY.create_from_config(
        {
            "config_list": config_list,
        }
    )
    with InMemoryCache(seed="") as cache:
        response = await client.create(messages=[{"role": "user", "content": "2+2="}], cache=cache)
        assert response["cached"] is False
        assert response["finish_reason"] == "stop"
        assert isinstance(response["content"], str)
        response_str = response["content"]
        actual_usage = client.actual_usage()
        total_usage = client.total_usage()

        response = await client.create(messages=[{"role": "user", "content": "2+2="}], cache=cache)
        assert response["cached"] is True
        assert response["finish_reason"] == "stop"
        assert isinstance(response["content"], str)
        assert response["content"] == response_str
        assert client.actual_usage() == actual_usage
        assert client.total_usage()["completion_tokens"] == total_usage["completion_tokens"] * 2
        assert client.actual_usage()["prompt_tokens"] == actual_usage["prompt_tokens"] * 2


@pytest.mark.skipif(skip_openai, reason="openai tests skipped")
@pytest.mark.asyncio
async def test_create_stream() -> None:
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        filter_dict={"api_type": ["azure"], "model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    client = DEFAULT_FACTORY.create_from_config(
        {
            "config_list": config_list,
        }
    )
    stream = client.create_stream(messages=[{"role": "user", "content": "2+2="}])
    content = ""
    result = None
    async for chunk in stream:
        if isinstance(chunk, str):
            content += chunk
        else:
            result = chunk

    assert isinstance(result, dict)
    assert result["cached"] is False
    assert result["finish_reason"] == "stop"
    assert isinstance(result["content"], str)
    assert content == result["content"]
