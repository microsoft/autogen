from unittest.mock import MagicMock, patch

import pytest

try:
    from openai.types.chat.chat_completion import ChatCompletionMessage, Choice

    from autogen.oai.together import TogetherClient, calculate_together_cost

    skip = False
except ImportError:
    TogetherClient = object
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
def together_client():
    return TogetherClient(api_key="fake_api_key")


# Test initialization and configuration
@pytest.mark.skipif(skip, reason="Together.AI dependency is not installed")
def test_initialization():

    # Missing any api_key
    with pytest.raises(AssertionError) as assertinfo:
        TogetherClient()  # Should raise an AssertionError due to missing api_key

    assert (
        "Please include the api_key in your config list entry for Together.AI or set the TOGETHER_API_KEY env variable."
        in str(assertinfo.value)
    )

    # Creation works
    TogetherClient(api_key="fake_api_key")  # Should create okay now.


# Test standard initialization
@pytest.mark.skipif(skip, reason="Together.AI dependency is not installed")
def test_valid_initialization(together_client):
    assert together_client.api_key == "fake_api_key", "Config api_key should be correctly set"


# Test parameters
@pytest.mark.skipif(skip, reason="Together.AI dependency is not installed")
def test_parsing_params(together_client):
    # All parameters
    params = {
        "model": "Qwen/Qwen2-72B-Instruct",
        "max_tokens": 1000,
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
        "top_k": 50,
        "repetition_penalty": 0.5,
        "presence_penalty": 1.5,
        "frequency_penalty": 1.5,
        "min_p": 0.2,
        "safety_model": "Meta-Llama/Llama-Guard-7b",
    }
    expected_params = {
        "model": "Qwen/Qwen2-72B-Instruct",
        "max_tokens": 1000,
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
        "top_k": 50,
        "repetition_penalty": 0.5,
        "presence_penalty": 1.5,
        "frequency_penalty": 1.5,
        "min_p": 0.2,
        "safety_model": "Meta-Llama/Llama-Guard-7b",
    }
    result = together_client.parse_params(params)
    assert result == expected_params

    # Only model, others set as defaults
    params = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
    }
    expected_params = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "max_tokens": 512,
        "stream": False,
        "temperature": None,
        "top_p": None,
        "top_k": None,
        "repetition_penalty": None,
        "presence_penalty": None,
        "frequency_penalty": None,
        "min_p": None,
        "safety_model": None,
    }
    result = together_client.parse_params(params)
    assert result == expected_params

    # Incorrect types, defaults should be set, will show warnings but not trigger assertions
    params = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "max_tokens": "512",
        "stream": "Yes",
        "temperature": "0.5",
        "top_p": "0.8",
        "top_k": "50",
        "repetition_penalty": "0.5",
        "presence_penalty": "1.5",
        "frequency_penalty": "1.5",
        "min_p": "0.2",
        "safety_model": False,
    }
    result = together_client.parse_params(params)
    assert result == expected_params

    # Values outside bounds, should warn and set to defaults
    params = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "max_tokens": -200,
        "presence_penalty": -5,
        "frequency_penalty": 5,
        "min_p": -0.5,
    }
    result = together_client.parse_params(params)
    assert result == expected_params


# Test cost calculation
@pytest.mark.skipif(skip, reason="Together.AI dependency is not installed")
def test_cost_calculation(mock_response):
    response = mock_response(
        text="Example response",
        choices=[{"message": "Test message 1"}],
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        cost=None,
        model="mistralai/Mixtral-8x22B-Instruct-v0.1",
    )
    assert (
        calculate_together_cost(response.usage["prompt_tokens"], response.usage["completion_tokens"], response.model)
        == 0.000018
    ), "Cost for this should be $0.000018"


# Test text generation
@pytest.mark.skipif(skip, reason="Together.AI dependency is not installed")
@patch("autogen.oai.together.TogetherClient.create")
def test_create_response(mock_create, together_client):
    # Mock TogetherClient.chat response
    mock_together_response = MagicMock()
    mock_together_response.choices = [
        MagicMock(finish_reason="stop", message=MagicMock(content="Example Llama response", tool_calls=None))
    ]
    mock_together_response.id = "mock_together_response_id"
    mock_together_response.model = "meta-llama/Llama-3-8b-chat-hf"
    mock_together_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)  # Example token usage

    mock_create.return_value = mock_together_response

    # Test parameters
    params = {
        "messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "World"}],
        "model": "meta-llama/Llama-3-8b-chat-hf",
    }

    # Call the create method
    response = together_client.create(params)

    # Assertions to check if response is structured as expected
    assert (
        response.choices[0].message.content == "Example Llama response"
    ), "Response content should match expected output"
    assert response.id == "mock_together_response_id", "Response ID should match the mocked response ID"
    assert response.model == "meta-llama/Llama-3-8b-chat-hf", "Response model should match the mocked response model"
    assert response.usage.prompt_tokens == 10, "Response prompt tokens should match the mocked response usage"
    assert response.usage.completion_tokens == 20, "Response completion tokens should match the mocked response usage"


# Test functions/tools
@pytest.mark.skipif(skip, reason="Together.AI dependency is not installed")
@patch("autogen.oai.together.TogetherClient.create")
def test_create_response_with_tool_call(mock_create, together_client):

    # Define the mock response directly within the patch
    mock_function = MagicMock(name="currency_calculator")
    mock_function.name = "currency_calculator"
    mock_function.arguments = '{"base_currency": "EUR", "quote_currency": "USD", "base_amount": 123.45}'

    # Define the mock response directly within the patch
    mock_create.return_value = MagicMock(
        choices=[
            MagicMock(
                finish_reason="tool_calls",
                message=MagicMock(
                    content="",  # Message is empty for tool responses
                    tool_calls=[MagicMock(id="gdRdrvnHh", function=mock_function)],
                ),
            )
        ],
        id="mock_together_response_id",
        model="meta-llama/Llama-3-8b-chat-hf",
        usage=MagicMock(prompt_tokens=10, completion_tokens=20),
    )

    # Test parameters
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
                        "base_currency": {
                            "enum": ["USD", "EUR"],
                            "type": "string",
                            "default": "USD",
                            "description": "Base currency",
                        },
                        "quote_currency": {
                            "enum": ["USD", "EUR"],
                            "type": "string",
                            "default": "EUR",
                            "description": "Quote currency",
                        },
                    },
                    "required": ["base_amount"],
                },
            },
        }
    ]

    together_messages = [
        {
            "role": "user",
            "content": "How much is 123.45 EUR in USD?",
            "name": None,
            "tool_calls": None,
            "tool_call_id": None,
        },
    ]

    # Call the create method (which is now mocked)
    response = together_client.create(
        {"messages": together_messages, "tools": converted_functions, "model": "meta-llama/Llama-3-8b-chat-hf"}
    )

    # Assertions to check if response is structured as expected
    assert response.choices[0].message.content == ""
    assert response.choices[0].message.tool_calls[0].function.name == "currency_calculator"
