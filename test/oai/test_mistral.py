from unittest.mock import MagicMock, patch

import pytest

try:
    from mistralai import (
        AssistantMessage,
        Function,
        FunctionCall,
        Mistral,
        SystemMessage,
        ToolCall,
        ToolMessage,
        UserMessage,
    )

    from autogen.oai.mistral import MistralAIClient, calculate_mistral_cost

    skip = False
except ImportError:
    MistralAIClient = object
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
def mistral_client():
    return MistralAIClient(api_key="fake_api_key")


# Test initialization and configuration
@pytest.mark.skipif(skip, reason="Mistral.AI dependency is not installed")
def test_initialization():

    # Missing any api_key
    with pytest.raises(AssertionError) as assertinfo:
        MistralAIClient()  # Should raise an AssertionError due to missing api_key

    assert (
        "Please specify the 'api_key' in your config list entry for Mistral or set the MISTRAL_API_KEY env variable."
        in str(assertinfo.value)
    )

    # Creation works
    MistralAIClient(api_key="fake_api_key")  # Should create okay now.


# Test standard initialization
@pytest.mark.skipif(skip, reason="Mistral.AI dependency is not installed")
def test_valid_initialization(mistral_client):
    assert mistral_client.api_key == "fake_api_key", "Config api_key should be correctly set"


# Test cost calculation
@pytest.mark.skipif(skip, reason="Mistral.AI dependency is not installed")
def test_cost_calculation(mock_response):
    response = mock_response(
        text="Example response",
        choices=[{"message": "Test message 1"}],
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        cost=None,
        model="mistral-large-latest",
    )
    assert calculate_mistral_cost(
        response.usage["prompt_tokens"], response.usage["completion_tokens"], response.model
    ) == (15 / 1000 * 0.0003), "Cost for this should be $0.0000045"


# Test text generation
@pytest.mark.skipif(skip, reason="Mistral.AI dependency is not installed")
@patch("autogen.oai.mistral.MistralAIClient.create")
def test_create_response(mock_chat, mistral_client):
    # Mock `mistral_response = client.chat.complete(**mistral_params)`
    mock_mistral_response = MagicMock()
    mock_mistral_response.choices = [
        MagicMock(finish_reason="stop", message=MagicMock(content="Example Mistral response", tool_calls=None))
    ]
    mock_mistral_response.id = "mock_mistral_response_id"
    mock_mistral_response.model = "mistral-small-latest"
    mock_mistral_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)  # Example token usage

    mock_chat.return_value = mock_mistral_response

    # Test parameters
    params = {
        "messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "World"}],
        "model": "mistral-small-latest",
    }

    # Call the create method
    response = mistral_client.create(params)

    # Assertions to check if response is structured as expected
    assert (
        response.choices[0].message.content == "Example Mistral response"
    ), "Response content should match expected output"
    assert response.id == "mock_mistral_response_id", "Response ID should match the mocked response ID"
    assert response.model == "mistral-small-latest", "Response model should match the mocked response model"
    assert response.usage.prompt_tokens == 10, "Response prompt tokens should match the mocked response usage"
    assert response.usage.completion_tokens == 20, "Response completion tokens should match the mocked response usage"


# Test functions/tools
@pytest.mark.skipif(skip, reason="Mistral.AI dependency is not installed")
@patch("autogen.oai.mistral.MistralAIClient.create")
def test_create_response_with_tool_call(mock_chat, mistral_client):
    # Mock `mistral_response = client.chat.complete(**mistral_params)`
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
        id="mock_mistral_response_id",
        model="mistral-small-latest",
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
    mistral_messages = [
        {"role": "user", "content": "How much is 123.45 EUR in USD?"},
        {"role": "assistant", "content": "World"},
    ]

    # Call the chat method
    response = mistral_client.create(
        {"messages": mistral_messages, "tools": converted_functions, "model": "mistral-medium-latest"}
    )

    # Assertions to check if the functions and content are included in the response
    assert response.choices[0].message.content == "Sample text about the functions"
    assert response.choices[0].message.tool_calls[0].function.name == "currency_calculator"
    assert response.choices[0].message.tool_calls[1].function.name == "get_weather"
