from unittest.mock import MagicMock, patch

import pytest

try:
    from autogen.oai.cerebras import CerebrasClient, calculate_cerebras_cost

    skip = False
except ImportError:
    CerebrasClient = object
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
def cerebras_client():
    return CerebrasClient(api_key="fake_api_key")


skip_reason = "Cerebras dependency is not installed"


# Test initialization and configuration
@pytest.mark.skipif(skip, reason=skip_reason)
def test_initialization():

    # Missing any api_key
    with pytest.raises(AssertionError) as assertinfo:
        CerebrasClient()  # Should raise an AssertionError due to missing api_key

    assert (
        "Please include the api_key in your config list entry for Cerebras or set the CEREBRAS_API_KEY env variable."
        in str(assertinfo.value)
    )

    # Creation works
    CerebrasClient(api_key="fake_api_key")  # Should create okay now.


# Test standard initialization
@pytest.mark.skipif(skip, reason=skip_reason)
def test_valid_initialization(cerebras_client):
    assert cerebras_client.api_key == "fake_api_key", "Config api_key should be correctly set"


# Test parameters
@pytest.mark.skipif(skip, reason=skip_reason)
def test_parsing_params(cerebras_client):
    # All parameters
    params = {
        "model": "llama3.1-8b",
        "max_tokens": 1000,
        "seed": 42,
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
    }
    expected_params = {
        "model": "llama3.1-8b",
        "max_tokens": 1000,
        "seed": 42,
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
    }
    result = cerebras_client.parse_params(params)
    assert result == expected_params

    # Only model, others set as defaults
    params = {
        "model": "llama3.1-8b",
    }
    expected_params = {
        "model": "llama3.1-8b",
        "max_tokens": None,
        "seed": None,
        "stream": False,
        "temperature": 1,
        "top_p": None,
    }
    result = cerebras_client.parse_params(params)
    assert result == expected_params

    # Incorrect types, defaults should be set, will show warnings but not trigger assertions
    params = {
        "model": "llama3.1-8b",
        "max_tokens": "1000",
        "seed": "42",
        "stream": "False",
        "temperature": "1",
        "top_p": "0.8",
    }
    result = cerebras_client.parse_params(params)
    assert result == expected_params

    # Values outside bounds, should warn and set to defaults
    params = {
        "model": "llama3.1-8b",
        "temperature": 33123,
    }
    result = cerebras_client.parse_params(params)
    assert result == expected_params

    # No model
    params = {
        "temperature": 1,
    }

    with pytest.raises(AssertionError) as assertinfo:
        result = cerebras_client.parse_params(params)

    assert "Please specify the 'model' in your config list entry to nominate the Cerebras model to use." in str(
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
        model="llama3.1-70b",
    )
    calculated_cost = calculate_cerebras_cost(
        response.usage["prompt_tokens"], response.usage["completion_tokens"], response.model
    )

    # Convert cost per milliion to cost per token.
    expected_cost = (
        response.usage["prompt_tokens"] * 0.6 / 1000000 + response.usage["completion_tokens"] * 0.6 / 1000000
    )

    assert calculated_cost == expected_cost, f"Cost for this should be ${expected_cost} but got ${calculated_cost}"


# Test text generation
@pytest.mark.skipif(skip, reason=skip_reason)
@patch("autogen.oai.cerebras.CerebrasClient.create")
def test_create_response(mock_chat, cerebras_client):
    # Mock CerebrasClient.chat response
    mock_cerebras_response = MagicMock()
    mock_cerebras_response.choices = [
        MagicMock(finish_reason="stop", message=MagicMock(content="Example Cerebras response", tool_calls=None))
    ]
    mock_cerebras_response.id = "mock_cerebras_response_id"
    mock_cerebras_response.model = "llama3.1-70b"
    mock_cerebras_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)  # Example token usage

    mock_chat.return_value = mock_cerebras_response

    # Test parameters
    params = {
        "messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "World"}],
        "model": "llama3.1-70b",
    }

    # Call the create method
    response = cerebras_client.create(params)

    # Assertions to check if response is structured as expected
    assert (
        response.choices[0].message.content == "Example Cerebras response"
    ), "Response content should match expected output"
    assert response.id == "mock_cerebras_response_id", "Response ID should match the mocked response ID"
    assert response.model == "llama3.1-70b", "Response model should match the mocked response model"
    assert response.usage.prompt_tokens == 10, "Response prompt tokens should match the mocked response usage"
    assert response.usage.completion_tokens == 20, "Response completion tokens should match the mocked response usage"


# Test functions/tools
@pytest.mark.skipif(skip, reason=skip_reason)
@patch("autogen.oai.cerebras.CerebrasClient.create")
def test_create_response_with_tool_call(mock_chat, cerebras_client):
    # Mock `cerebras_response = client.chat(**cerebras_params)`
    mock_function = MagicMock(name="currency_calculator")
    mock_function.name = "currency_calculator"
    mock_function.arguments = '{"base_currency": "EUR", "quote_currency": "USD", "base_amount": 123.45}'

    mock_function_2 = MagicMock(name="get_weather")
    mock_function_2.name = "get_weather"
    mock_function_2.arguments = '{"location": "Chicago"}'

    mock_chat.return_value = MagicMock(
        choices=[
            MagicMock(
                finish_reason="tool_calls",
                message=MagicMock(
                    content="Sample text about the functions",
                    tool_calls=[
                        MagicMock(id="gdRdrvnHh", function=mock_function),
                        MagicMock(id="abRdrvnHh", function=mock_function_2),
                    ],
                ),
            )
        ],
        id="mock_cerebras_response_id",
        model="llama3.1-70b",
        usage=MagicMock(prompt_tokens=10, completion_tokens=20),
    )

    # Construct parameters
    converted_functions = [
        {
            "type": "function",
            "function": {
                "description": "Currency exchange calculator.",
                "name": "currency_calculator",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "base_amount": {"type": "number", "description": "Amount of currency in base_currency"},
                    },
                    "required": ["base_amount"],
                },
            },
        }
    ]
    cerebras_messages = [
        {"role": "user", "content": "How much is 123.45 EUR in USD?"},
        {"role": "assistant", "content": "World"},
    ]

    # Call the create method
    response = cerebras_client.create(
        {"messages": cerebras_messages, "tools": converted_functions, "model": "llama3.1-70b"}
    )

    # Assertions to check if the functions and content are included in the response
    assert response.choices[0].message.content == "Sample text about the functions"
    assert response.choices[0].message.tool_calls[0].function.name == "currency_calculator"
    assert response.choices[0].message.tool_calls[1].function.name == "get_weather"
