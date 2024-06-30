from unittest.mock import MagicMock, patch

import pytest

try:
    from autogen.oai.yi import YiClient, calculate_yi_cost, YI_PRICING_1K

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
    assert yi_client._oai_client.api_key == "fake_api_key", "Config api_key should be correctly set"


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
        "messages": [],
        "max_tokens": 1000,
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
    }
    result = yi_client.parse_params(params)
    assert result == expected_params, f"{result=}, {params=}"

    # Only model, others set as defaults
    params = {
        "model": "yi-large",
    }
    expected_params = {
        "model": "yi-large",
        "messages": [],
        "max_tokens": None,
        "stream": False,
        "temperature": 0.3,
        "top_p": 0.9,
    }
    result = yi_client.parse_params(params)
    assert result == expected_params, f"{result=}, {params=}"

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
    correct_cost = YI_PRICING_1K[response.model][0] * response.usage["prompt_tokens"] / 1000 + YI_PRICING_1K[response.model][1] * response.usage["completion_tokens"] / 1000
    assert (
        calculate_yi_cost(response.usage["prompt_tokens"], response.usage["completion_tokens"], response.model)
        == correct_cost
    ), f"Cost for this should be ${correct_cost}"


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
        "model": "yi-large",
    }

    # Call the create method
    response = yi_client.create(params)

    # Assertions to check if response is structured as expected
    assert (
        response.choices[0].message.content == "Example Yi response"
    ), "Response content should match expected output"
    assert response.id == "mock_yi_response_id", "Response ID should match the mocked response ID"
    assert response.model == "yi-large", "Response model should match the mocked response model"
    assert response.usage.prompt_tokens == 10, "Response prompt tokens should match the mocked response usage"
    assert response.usage.completion_tokens == 20, "Response completion tokens should match the mocked response usage"


# Test functions/tools
@pytest.mark.skipif(skip, reason=skip_reason)
@patch("autogen.oai.yi.YiClient.create")
def test_create_response_with_tool_call(mock_chat, yi_client):
    # Mock `yi_response = client.chat(**yi_params)`
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
        id="mock_yi_response_id",
        model="yi-large",
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
    yi_messages = [
        {"role": "user", "content": "How much is 123.45 EUR in USD?"},
        {"role": "assistant", "content": "World"},
    ]

    # Call the create method
    response = yi_client.create({"messages": yi_messages, "tools": converted_functions, "model": "yi-large"})

    # Assertions to check if the functions and content are included in the response
    assert response.choices[0].message.content == "Sample text about the functions"
    assert response.choices[0].message.tool_calls[0].function.name == "currency_calculator"
    assert response.choices[0].message.tool_calls[1].function.name == "get_weather"
