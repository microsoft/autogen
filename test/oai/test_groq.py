from unittest.mock import MagicMock, patch

import pytest

try:
    from autogen.oai.groq import GroqClient, calculate_groq_cost

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
def groq_client():
    return GroqClient(api_key="fake_api_key")


skip_reason = "Groq dependency is not installed"


# Test initialization and configuration
@pytest.mark.skipif(skip, reason=skip_reason)
def test_initialization():

    # Missing any api_key
    with pytest.raises(AssertionError) as assertinfo:
        GroqClient()  # Should raise an AssertionError due to missing api_key

    assert "Please include the api_key in your config list entry for Groq or set the GROQ_API_KEY env variable." in str(
        assertinfo.value
    )

    # Creation works
    GroqClient(api_key="fake_api_key")  # Should create okay now.


# Test standard initialization
@pytest.mark.skipif(skip, reason=skip_reason)
def test_valid_initialization(groq_client):
    assert groq_client.api_key == "fake_api_key", "Config api_key should be correctly set"


# Test parameters
@pytest.mark.skipif(skip, reason=skip_reason)
def test_parsing_params(groq_client):
    # All parameters
    params = {
        "model": "llama3-8b-8192",
        "frequency_penalty": 1.5,
        "presence_penalty": 1.5,
        "max_tokens": 1000,
        "seed": 42,
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
    }
    expected_params = {
        "model": "llama3-8b-8192",
        "frequency_penalty": 1.5,
        "presence_penalty": 1.5,
        "max_tokens": 1000,
        "seed": 42,
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
    }
    result = groq_client.parse_params(params)
    assert result == expected_params

    # Only model, others set as defaults
    params = {
        "model": "llama3-8b-8192",
    }
    expected_params = {
        "model": "llama3-8b-8192",
        "frequency_penalty": None,
        "presence_penalty": None,
        "max_tokens": None,
        "seed": None,
        "stream": False,
        "temperature": 1,
        "top_p": None,
    }
    result = groq_client.parse_params(params)
    assert result == expected_params

    # Incorrect types, defaults should be set, will show warnings but not trigger assertions
    params = {
        "model": "llama3-8b-8192",
        "frequency_penalty": "1.5",
        "presence_penalty": "1.5",
        "max_tokens": "1000",
        "seed": "42",
        "stream": "False",
        "temperature": "1",
        "top_p": "0.8",
    }
    result = groq_client.parse_params(params)
    assert result == expected_params

    # Values outside bounds, should warn and set to defaults
    params = {
        "model": "llama3-8b-8192",
        "frequency_penalty": 5000,
        "presence_penalty": -500,
        "temperature": 3,
    }
    result = groq_client.parse_params(params)
    assert result == expected_params

    # No model
    params = {
        "frequency_penalty": 1,
    }

    with pytest.raises(AssertionError) as assertinfo:
        result = groq_client.parse_params(params)

    assert "Please specify the 'model' in your config list entry to nominate the Groq model to use." in str(
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
        model="llama3-70b-8192",
    )
    assert (
        calculate_groq_cost(response.usage["prompt_tokens"], response.usage["completion_tokens"], response.model)
        == 0.000532
    ), "Cost for this should be $0.000532"


# Test text generation
@pytest.mark.skipif(skip, reason=skip_reason)
@patch("autogen.oai.groq.GroqClient.create")
def test_create_response(mock_chat, groq_client):
    # Mock GroqClient.chat response
    mock_groq_response = MagicMock()
    mock_groq_response.choices = [
        MagicMock(finish_reason="stop", message=MagicMock(content="Example Groq response", tool_calls=None))
    ]
    mock_groq_response.id = "mock_groq_response_id"
    mock_groq_response.model = "llama3-70b-8192"
    mock_groq_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)  # Example token usage

    mock_chat.return_value = mock_groq_response

    # Test parameters
    params = {
        "messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "World"}],
        "model": "llama3-70b-8192",
    }

    # Call the create method
    response = groq_client.create(params)

    # Assertions to check if response is structured as expected
    assert (
        response.choices[0].message.content == "Example Groq response"
    ), "Response content should match expected output"
    assert response.id == "mock_groq_response_id", "Response ID should match the mocked response ID"
    assert response.model == "llama3-70b-8192", "Response model should match the mocked response model"
    assert response.usage.prompt_tokens == 10, "Response prompt tokens should match the mocked response usage"
    assert response.usage.completion_tokens == 20, "Response completion tokens should match the mocked response usage"


# Test functions/tools
@pytest.mark.skipif(skip, reason=skip_reason)
@patch("autogen.oai.groq.GroqClient.create")
def test_create_response_with_tool_call(mock_chat, groq_client):
    # Mock `groq_response = client.chat(**groq_params)`
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
        id="mock_groq_response_id",
        model="llama3-70b-8192",
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
    groq_messages = [
        {"role": "user", "content": "How much is 123.45 EUR in USD?"},
        {"role": "assistant", "content": "World"},
    ]

    # Call the create method
    response = groq_client.create({"messages": groq_messages, "tools": converted_functions, "model": "llama3-70b-8192"})

    # Assertions to check if the functions and content are included in the response
    assert response.choices[0].message.content == "Sample text about the functions"
    assert response.choices[0].message.tool_calls[0].function.name == "currency_calculator"
    assert response.choices[0].message.tool_calls[1].function.name == "get_weather"
