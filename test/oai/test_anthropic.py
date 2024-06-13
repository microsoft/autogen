#!/usr/bin/env python3 -m pytest

import os

import pytest

try:
    from openai.types.chat.chat_completion import ChatCompletionMessage

    from autogen.oai.anthropic import AnthropicClient, calculate_cost

    skip = False
except ImportError:
    AnthropicClient = object
    InternalServerError = object
    skip = True

reason = "Anthropic dependency not installed"


@pytest.fixture()
def anthropic_client():
    return AnthropicClient(api_key="dummy_api_key")


@pytest.mark.skipif(skip, reason=reason)
def test_initialization_missing_api_key():
    with pytest.raises(AssertionError) as exc_info:
        AnthropicClient()
    assert "Please provide an `api_key`" in str(exc_info.value)

    AnthropicClient(api_key="dummy_api_key")


@pytest.mark.skipif(skip, reason=reason)
def test_intialization(anthropic_client):
    assert anthropic_client.api_key == "dummy_api_key", "`api_key` should be correctly set in the config"


@pytest.mark.skipif(skip, reason=reason)
def test_calculate_cost(anthropic_client):
    response = {
        "content": [{"text": "Hi! My name is Claude.", "type": "text"}],
        "id": "msg_013Zva2CMHLNnXjNJJKqJ2EF",
        "model": "claude-3-opus-20240229",
        "role": "assistant",
        "stop_reason": "end_turn",
        "stop_sequence": "null",
        "type": "message",
        "usage": {"input_tokens": 10, "output_tokens": 25},
    }
    cost = calculate_cost(anthropic_client, response)
    assert cost == 0.002025, "Cost should be calculated correctly"


@pytest.mark.skipif(skip, reason=reason)
def test_load_config(anthropic_client):
    # All parameters
    params = {
        "model": "claude-3-sonnet-20240229",
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
        "max_tokens": 100,
    }
    expected_params = {
        "model": "claude-3-sonnet-20240229",
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
        "max_tokens": 100,
    }
    result = anthropic_client.load_config(params)
    assert result == expected_params
