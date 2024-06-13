#!/usr/bin/env python3 -m pytest

import os
import shutil
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
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
    config = {
        "model": "claude-3-sonnet-20240229",
        "api_key": "dummy_api_key",
    }
    return AnthropicClient(config=config)


@pytest.mark.skipif(skip, reason=reason)
def test_anthropic_client():
    with pytest.raises(AssertionError) as assertinfo:
        AnthropicClient()  # Should raise an AssertionError due to missing api_key

    assert (
        "Please specify the 'api_key' in your config list entry for Mistral or set the MISTRAL_API_KEY env variable."
        in str(assertinfo.value)
    )

    # Creation works
    config = {
        "model": "claude-3-sonnet-20240229",
        "api_key": "dummy_api_key",
    }
    AnthropicClient(config=config)  # Should create okay now.


@pytest.mark.skipif(skip, reason=reason)
def test_intialization(anthropic_client):
    assert anthropic_client.api_key == "dummy_api_key", "`api_key` should be correctly set in the config"
