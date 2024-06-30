from unittest.mock import MagicMock, patch

import pytest

try:
    from autogen.oai.yi import YiClient, calculate_yi_cost

    skip = False
except ImportError:
    YiClient = object
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
def yi_client():
    return YiClient(api_key="fake_api_key")


skip_reason = "Yi dependency is not installed"


# Test initialization and configuration
@pytest.mark.skipif(skip, reason=skip_reason)
def test_initialization():

    # Missing any api_key
    with pytest.raises(AssertionError) as assertinfo:
        YiClient()  # Should raise an AssertionError due to missing api_key

    assert "Please include the api_key in your config list entry for Yi or set the YI_API_KEY env variable." in str(
        assertinfo.value
    )

    # Creation works
    YiClient(api_key="fake_api_key")  # Should create okay now.


# Test standard initialization
@pytest.mark.skipif(skip, reason=skip_reason)
def test_valid_initialization(yi_client):
    assert yi_client.api_key == "fake_api_key", "Config api_key should be correctly set"


# Test parameters
@pytest.mark.skipif(skip, reason=skip_reason)
def test_parsing_params(yi_client):
    # All parameters
    params = {
        "model": "yi-large",
        "frequency_penalty": 1.5,
        "presence_penalty": 1.5,
        "max_tokens": 1000,
        "seed": 42,
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
    }
    expected_params = {
        "model": "yi-large",
        "max_tokens": 1000,
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
    }
    result = yi_client.parse_params(params)
    assert result == expected_params

    # Only model, others set as defaults
    params = {
        "model": "yi-large",
    }
    expected_params = {
        "model": "yi-large",
        "max_tokens": None,
        "stream": False,
        "temperature": 0.3,
        "top_p": 0.9,
    }
    result = yi_client.parse_params(params)
    assert result == expected_params

    # Incorrect types, defaults should be set, will show warnings but not trigger assertions
    params = {
        "model": "yi-large",
        "frequency_penalty": "1.5",
        "presence_penalty": "1.5",
        "max_tokens": "1000",
        "seed": "42",
        "stream": "False",
        "temperature": "1",
        "top_p": "0.8",
    }
    result = yi_client.parse_params(params)
    assert result == expected_params

    # Values outside bounds, should warn and set to defaults
    params = {
        "model": "yi-large",
        "frequency_penalty": 5000,
        "presence_penalty": -500,
        "temperature": 3,
    }
    result = yi_client.parse_params(params)
    assert result == expected_params

    # No model
    params = {
        "frequency_penalty": 1,
    }

    with pytest.raises(AssertionError) as assertinfo:
        result = yi_client.parse_params(params)

    assert "Please specify the 'model' in your config list entry to nominate the Yi model to use." in str(
        assertinfo.value
    )


# Test cost calculation
@pytest.mark.skipif(skip, reason=skip_reason)
def test_cost_calculation(mock_response):
    response = mock_response(
        text="Example response",
        choices=[{"message": "Test message 1"}],
        usage={"prompt_tokens": 500, "completion_tokens": 300, "total_tokens": 800},
        cost=None,
        model="yi-large",
    )
    assert (
        calculate_yi_cost(response.usage["prompt_tokens"], response.usage["completion_tokens"], response.model)
        == 0.000532
    ), "Cost for this should be $0.000532"


# Test text generation
@pytest.mark.skipif(skip, reason=skip_reason)
@patch("autogen.oai.yi.YiClient.create")
def test_create_response(mock_chat, yi_client):
    # Mock YiClient.chat response
    mock_yi_response = MagicMock()
    mock_yi_response.choices = [
        MagicMock(finish_reason="stop", message=MagicMock(content="Example Yi response", tool_calls=None))
    ]
    mock_yi_response.id = "mock_yi_response_id"
    mock_yi_response.model = "yi-large"
    mock_yi_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)  # Example token usage

    mock_chat.return_value = mock_yi_response

    # Test parameters
    params = {
        "messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "World"}],
        "model": "llama3-70b-8192",
    }

    # Call the create method
    response = yi_client.create(params)

    # Assertions to check if response is structured as expected
    assert (
        response.choices[0].message.content == "Example Yi response"
    ), "Response content should match expected output"
    assert response.id == "mock_yi_response_id", "Response ID should match the mocked response ID"
    assert response.model == "llama3-70b-8192", "Response model should match the mocked response model"
    assert response.usage.prompt_tokens == 10, "Response prompt tokens should match the mocked response usage"
    assert response.usage.completion_tokens == 20, "Response completion tokens should match the mocked response usage"
