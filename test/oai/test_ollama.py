from unittest.mock import MagicMock, patch

import pytest

try:
    from autogen.oai.ollama import OllamaClient, response_to_tool_call

    skip = False
except ImportError:
    OllamaClient = object
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
def ollama_client():

    # Set Ollama client with some default values
    client = OllamaClient()

    client._native_tool_calls = True
    client._tools_in_conversation = False

    return client


skip_reason = "Ollama dependency is not installed"


# Test initialization and configuration
@pytest.mark.skipif(skip, reason=skip_reason)
def test_initialization():

    # Creation works without an api_key
    OllamaClient()


# Test parameters
@pytest.mark.skipif(skip, reason=skip_reason)
def test_parsing_params(ollama_client):
    # All parameters (with default values)
    params = {
        "model": "llama3.1:8b",
        "temperature": 0.8,
        "num_predict": 128,
        "repeat_penalty": 1.1,
        "seed": 42,
        "top_k": 40,
        "top_p": 0.9,
        "stream": False,
    }
    expected_params = {
        "model": "llama3.1:8b",
        "temperature": 0.8,
        "num_predict": 128,
        "top_k": 40,
        "top_p": 0.9,
        "options": {
            "repeat_penalty": 1.1,
            "seed": 42,
        },
        "stream": False,
    }
    result = ollama_client.parse_params(params)
    assert result == expected_params

    # Incorrect types, defaults should be set, will show warnings but not trigger assertions
    params = {
        "model": "llama3.1:8b",
        "temperature": "0.5",
        "num_predict": "128",
        "repeat_penalty": "1.1",
        "seed": "42",
        "top_k": "40",
        "top_p": "0.9",
        "stream": "True",
    }
    result = ollama_client.parse_params(params)
    assert result == expected_params

    # Only model, others set as defaults if they are mandatory
    params = {
        "model": "llama3.1:8b",
    }
    expected_params = {"model": "llama3.1:8b", "stream": False}
    result = ollama_client.parse_params(params)
    assert result == expected_params

    # No model
    params = {
        "temperature": 0.8,
    }

    with pytest.raises(AssertionError) as assertinfo:
        result = ollama_client.parse_params(params)

    assert "Please specify the 'model' in your config list entry to nominate the Ollama model to use." in str(
        assertinfo.value
    )


# Test text generation
@pytest.mark.skipif(skip, reason=skip_reason)
@patch("autogen.oai.ollama.OllamaClient.create")
def test_create_response(mock_chat, ollama_client):
    # Mock OllamaClient.chat response
    mock_ollama_response = MagicMock()
    mock_ollama_response.choices = [
        MagicMock(finish_reason="stop", message=MagicMock(content="Example Ollama response", tool_calls=None))
    ]
    mock_ollama_response.id = "mock_ollama_response_id"
    mock_ollama_response.model = "llama3.1:8b"
    mock_ollama_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)  # Example token usage

    mock_chat.return_value = mock_ollama_response

    # Test parameters
    params = {
        "messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "World"}],
        "model": "llama3.1:8b",
    }

    # Call the create method
    response = ollama_client.create(params)

    # Assertions to check if response is structured as expected
    assert (
        response.choices[0].message.content == "Example Ollama response"
    ), "Response content should match expected output"
    assert response.id == "mock_ollama_response_id", "Response ID should match the mocked response ID"
    assert response.model == "llama3.1:8b", "Response model should match the mocked response model"
    assert response.usage.prompt_tokens == 10, "Response prompt tokens should match the mocked response usage"
    assert response.usage.completion_tokens == 20, "Response completion tokens should match the mocked response usage"


# Test functions/tools
@pytest.mark.skipif(skip, reason=skip_reason)
@patch("autogen.oai.ollama.OllamaClient.create")
def test_create_response_with_tool_call(mock_chat, ollama_client):
    # Mock OllamaClient.chat response
    mock_function = MagicMock(name="currency_calculator")
    mock_function.name = "currency_calculator"
    mock_function.arguments = '{"base_currency": "EUR", "quote_currency": "USD", "base_amount": 123.45}'

    mock_function_2 = MagicMock(name="get_weather")
    mock_function_2.name = "get_weather"
    mock_function_2.arguments = '{"location": "New York"}'

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
        id="mock_ollama_response_id",
        model="llama3.1:8b",
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
    ollama_messages = [
        {"role": "user", "content": "How much is 123.45 EUR in USD?"},
        {"role": "assistant", "content": "World"},
    ]

    # Call the create method
    response = ollama_client.create({"messages": ollama_messages, "tools": converted_functions, "model": "llama3.1:8b"})

    # Assertions to check if the functions and content are included in the response
    assert response.choices[0].message.content == "Sample text about the functions"
    assert response.choices[0].message.tool_calls[0].function.name == "currency_calculator"
    assert response.choices[0].message.tool_calls[1].function.name == "get_weather"


# Test function parsing with manual tool calling
@pytest.mark.skipif(skip, reason=skip_reason)
def test_manual_tool_calling_parsing(ollama_client):
    # Test the parsing of a tool call within the response content (fully correct)
    response_content = """[{"name": "weather_forecast", "arguments":{"location": "New York"}},{"name": "currency_calculator", "arguments":{"base_amount": 123.45, "quote_currency": "EUR", "base_currency": "USD"}}]"""

    response_tool_calls = response_to_tool_call(response_content)

    expected_tool_calls = [
        {"name": "weather_forecast", "arguments": {"location": "New York"}},
        {
            "name": "currency_calculator",
            "arguments": {"base_amount": 123.45, "quote_currency": "EUR", "base_currency": "USD"},
        },
    ]

    assert (
        response_tool_calls == expected_tool_calls
    ), "Manual Tool Calling Parsing of response did not yield correct tool_calls (full string match)"

    # Test the parsing with a substring containing the response content (should still pass)
    response_content = """I will call two functions, weather_forecast and currency_calculator:\n[{"name": "weather_forecast", "arguments":{"location": "New York"}},{"name": "currency_calculator", "arguments":{"base_amount": 123.45, "quote_currency": "EUR", "base_currency": "USD"}}]"""

    response_tool_calls = response_to_tool_call(response_content)

    assert (
        response_tool_calls == expected_tool_calls
    ), "Manual Tool Calling Parsing of response did not yield correct tool_calls (partial string match)"

    # Test the parsing with an invalid function call
    response_content = """[{"function": "weather_forecast", "args":{"location": "New York"}},{"function": "currency_calculator", "args":{"base_amount": 123.45, "quote_currency": "EUR", "base_currency": "USD"}}]"""

    response_tool_calls = response_to_tool_call(response_content)

    assert (
        response_tool_calls is None
    ), "Manual Tool Calling Parsing of response did not yield correct tool_calls (invalid function call)"

    # Test the parsing with plain text
    response_content = """Call the weather_forecast function and pass in 'New York' as the 'location' argument."""

    response_tool_calls = response_to_tool_call(response_content)

    assert (
        response_tool_calls is None
    ), "Manual Tool Calling Parsing of response did not yield correct tool_calls (no function in text)"


# Test message conversion from OpenAI to Ollama format
@pytest.mark.skipif(skip, reason=skip_reason)
def test_oai_messages_to_ollama_messages(ollama_client):
    # Test that the "name" key is removed
    test_messages = [
        {"role": "system", "content": "You are a helpful AI bot."},
        {"role": "user", "name": "anne", "content": "Why is the sky blue?"},
    ]
    messages = ollama_client.oai_messages_to_ollama_messages(test_messages, None)

    expected_messages = [
        {"role": "system", "content": "You are a helpful AI bot."},
        {"role": "user", "content": "Why is the sky blue?"},
    ]

    assert messages == expected_messages, "'name' was not removed from messages"

    # Test that there isn't a final system message and it's changed to user
    test_messages.append({"role": "system", "content": "Summarise the conversation."})

    messages = ollama_client.oai_messages_to_ollama_messages(test_messages, None)

    expected_messages = [
        {"role": "system", "content": "You are a helpful AI bot."},
        {"role": "user", "content": "Why is the sky blue?"},
        {"role": "user", "content": "Summarise the conversation."},
    ]

    assert messages == expected_messages, "Final 'system' message was not changed to 'user'"

    # Test that the last message is a user or system message and if not, add a continue message
    test_messages[2] = {"role": "assistant", "content": "The sky is blue because that's a great colour."}

    messages = ollama_client.oai_messages_to_ollama_messages(test_messages, None)

    expected_messages = [
        {"role": "system", "content": "You are a helpful AI bot."},
        {"role": "user", "content": "Why is the sky blue?"},
        {"role": "assistant", "content": "The sky is blue because that's a great colour."},
        {"role": "user", "content": "Please continue."},
    ]

    assert messages == expected_messages, "'Please continue' message was not appended."
