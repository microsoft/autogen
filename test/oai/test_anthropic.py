#!/usr/bin/env python3 -m pytest

import os
from unittest.mock import MagicMock, patch

import pytest

try:
    from autogen.oai.anthropic import AnthropicClient, _calculate_cost

    skip = False
except ImportError:
    AnthropicClient = object
    skip = True

from typing_extensions import Literal

reason = "Anthropic dependency not installed!"


@pytest.fixture()
def mock_completion():
    class MockCompletion:
        def __init__(
            self,
            id="msg_013Zva2CMHLNnXjNJJKqJ2EF",
            completion="Hi! My name is Claude.",
            model="claude-3-opus-20240229",
            stop_reason="end_turn",
            role="assistant",
            type: Literal["completion"] = "completion",
            usage={"input_tokens": 10, "output_tokens": 25},
        ):
            self.id = id
            self.role = role
            self.completion = completion
            self.model = model
            self.stop_reason = stop_reason
            self.type = type
            self.usage = usage

    return MockCompletion


@pytest.fixture()
def anthropic_client():
    return AnthropicClient(api_key="dummy_api_key")


@pytest.mark.skipif(skip, reason=reason)
def test_initialization_missing_api_key():
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("AWS_ACCESS_KEY", None)
    os.environ.pop("AWS_SECRET_KEY", None)
    os.environ.pop("AWS_SESSION_TOKEN", None)
    os.environ.pop("AWS_REGION", None)
    with pytest.raises(ValueError, match="API key or AWS credentials are required to use the Anthropic API."):
        AnthropicClient()

    AnthropicClient(api_key="dummy_api_key")


@pytest.fixture()
def anthropic_client_with_aws_credentials():
    return AnthropicClient(
        aws_access_key="dummy_access_key",
        aws_secret_key="dummy_secret_key",
        aws_session_token="dummy_session_token",
        aws_region="us-west-2",
    )


@pytest.mark.skipif(skip, reason=reason)
def test_intialization(anthropic_client):
    assert anthropic_client.api_key == "dummy_api_key", "`api_key` should be correctly set in the config"


@pytest.mark.skipif(skip, reason=reason)
def test_intialization_with_aws_credentials(anthropic_client_with_aws_credentials):
    assert (
        anthropic_client_with_aws_credentials.aws_access_key == "dummy_access_key"
    ), "`aws_access_key` should be correctly set in the config"
    assert (
        anthropic_client_with_aws_credentials.aws_secret_key == "dummy_secret_key"
    ), "`aws_secret_key` should be correctly set in the config"
    assert (
        anthropic_client_with_aws_credentials.aws_session_token == "dummy_session_token"
    ), "`aws_session_token` should be correctly set in the config"
    assert (
        anthropic_client_with_aws_credentials.aws_region == "us-west-2"
    ), "`aws_region` should be correctly set in the config"


# Test cost calculation
@pytest.mark.skipif(skip, reason=reason)
def test_cost_calculation(mock_completion):
    completion = mock_completion(
        completion="Hi! My name is Claude.",
        usage={"prompt_tokens": 10, "completion_tokens": 25, "total_tokens": 35},
        model="claude-3-opus-20240229",
    )
    assert (
        _calculate_cost(completion.usage["prompt_tokens"], completion.usage["completion_tokens"], completion.model)
        == 0.002025
    ), "Cost should be $0.002025"


@pytest.mark.skipif(skip, reason=reason)
def test_load_config(anthropic_client):
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
        "stop_sequences": None,
        "top_k": None,
    }
    result = anthropic_client.load_config(params)
    assert result == expected_params, "Config should be correctly loaded"
