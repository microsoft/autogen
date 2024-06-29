from unittest.mock import MagicMock, patch

import pytest

try:
    from autogen.oai.litellm import LiteLLMClient

    skip = False
except ImportError:
    GroqClient = object
    InternalServerError = object
    skip = True


# Fixtures for mock data
@pytest.fixture
def mock_response():
    class MockResponse:
        def __init__(self, text, choices, usage, cost, model):
            self.text = text
            self.choices = choices
            self.usage = usage
            self.cost = cost
            self.model = model

    return MockResponse


@pytest.fixture
def litellm_client():
    return LiteLLMClient(api_key="fake_api_key")


skip_reason = "LiteLLM dependency is not installed"


# Test initialization and configuration
@pytest.mark.skipif(skip, reason=skip_reason)
def test_initialization():

    # Missing any api_key
    with pytest.raises(AssertionError) as assertinfo:
        LiteLLMClient()  # Should raise an AssertionError due to missing api_key

    assert (
        "Please include the api_key in your config list entry for LiteLLM or set the LiteLLM_API_KEY env variable."
        in str(assertinfo.value)
    )

    # Creation works
    LiteLLMClient(api_key="fake_api_key")  # Should create okay now.
    assert False  # BREAK!
