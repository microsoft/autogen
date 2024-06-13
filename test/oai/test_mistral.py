from unittest.mock import MagicMock, patch

import pytest

try:
    from mistralai.models.chat_completion import ChatMessage

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


# Test parameters
@pytest.mark.skipif(skip, reason="Mistral.AI dependency is not installed")
def test_parsing_params(mistral_client):
    # All parameters
    params = {
        "model": "mistral-medium-latest",
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
        "max_tokens": 100,
        "safe_prompt": True,
        "random_seed": 42,
    }
    expected_params = {
        "model": "mistral-medium-latest",
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
        "max_tokens": 100,
        "safe_prompt": True,
        "random_seed": 42,
    }
    result = mistral_client.parse_params(params)
    assert result == expected_params

    # Only model, others set as defaults
    params = {
        "model": "mistral-medium-latest",
    }
    expected_params = {
        "model": "mistral-medium-latest",
        "stream": False,
        "temperature": 0.7,
        "top_p": None,
        "max_tokens": None,
        "safe_prompt": False,
        "random_seed": None,
    }
    result = mistral_client.parse_params(params)
    assert result == expected_params

    # Incorrect types, defaults should be set, will show warnings but not trigger assertions
    params = {
        "model": "mistral-medium-latest",
        "stream": 13,
        "temperature": "0.7",
        "top_p": "0.3",
        "max_tokens": "True",
        "safe_prompt": "True",
        "random_seed": "False",
    }
    expected_params = {
        "model": "mistral-medium-latest",
        "stream": False,
        "temperature": 0.7,
        "top_p": None,
        "max_tokens": None,
        "safe_prompt": False,
        "random_seed": None,
    }
    result = mistral_client.parse_params(params)
    assert result == expected_params


# Test cost calculation
@pytest.mark.skipif(skip, reason="Mistral.AI dependency is not installed")
def test_cost_calculation(mistral_client, mock_response):
    response = mock_response(
        text="Example response",
        choices=[{"message": "Test message 1"}],
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        cost=None,
        model="mistral-large-latest",
    )
    assert (
        calculate_mistral_cost(response.usage["prompt_tokens"], response.usage["completion_tokens"], response.model)
        == 0.0001
    ), "Cost for this should be $0.0001"


# Test text generation
@pytest.mark.skipif(skip, reason="Mistral.AI dependency is not installed")
@patch("autogen.oai.mistral.MistralClient.chat")
def test_create_response(mock_chat, mistral_client):
    # Mock MistralClient.chat response
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
def test_create_response_with_tool_call(mock_create, mistral_client):

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
        id="mock_mistral_response_id",
        model="mistral-small-latest",
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

    mistral_messages = [
        ChatMessage(
            role="system",
            content='For currency exchange tasks,\n        only use the functions you have been provided with.\n        Output \'TERMINATE\' when an answer has been provided.\n        Do not include the function name or result in the JSON.\n        Example of the return JSON is:\n        {\n            "parameter_1_name": 100.00,\n            "parameter_2_name": "ABC",\n            "parameter_3_name": "DEF",\n        }.\n        Another example of the return JSON is:\n        {\n            "parameter_1_name": "GHI",\n            "parameter_2_name": "ABC",\n            "parameter_3_name": "DEF",\n            "parameter_4_name": 123.00,\n        }. ',
            name=None,
            tool_calls=None,
            tool_call_id=None,
        ),
        ChatMessage(
            role="user", content="How much is 123.45 EUR in USD?", name=None, tool_calls=None, tool_call_id=None
        ),
    ]

    # Call the create method (which is now mocked)
    response = mistral_client.create(
        {"messages": mistral_messages, "tools": converted_functions, "model": "mistral-small-latest"}
    )

    # Assertions to check if response is structured as expected
    assert response.id == "mock_mistral_response_id"
    assert response.model == "mistral-small-latest"
    assert response.usage.prompt_tokens == 10
    assert response.usage.completion_tokens == 20
    assert len(response.choices) == 1
    assert response.choices[0].finish_reason == "tool_calls"
    assert response.choices[0].message.content == ""
    assert len(response.choices[0].message.tool_calls) == 1
    assert response.choices[0].message.tool_calls[0].id == "gdRdrvnHh"
    assert response.choices[0].message.tool_calls[0].function.name == "currency_calculator"
    assert (
        response.choices[0].message.tool_calls[0].function.arguments
        == '{"base_currency": "EUR", "quote_currency": "USD", "base_amount": 123.45}'
    )
