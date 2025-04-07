from unittest.mock import MagicMock, patch

import pytest

try:
    from autogen.oai.bedrock import BedrockClient, oai_messages_to_bedrock_messages

    skip = False
except ImportError:
    BedrockClient = object
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
def bedrock_client():

    # Set Bedrock client with some default values
    client = BedrockClient()

    client._supports_system_prompts = True

    return client


skip_reason = "Amazon Bedrock dependency is not installed"


# Test initialization and configuration
@pytest.mark.skipif(skip, reason=skip_reason)
def test_initialization():

    # Creation works without an api_key as it's handled in the parameter parsing
    BedrockClient()


# Test parameters
@pytest.mark.skipif(skip, reason=skip_reason)
def test_parsing_params(bedrock_client):
    # All parameters (with default values)
    params = {
        # "aws_region_name": "us-east-1",
        # "aws_access_key_id": "test_access_key_id",
        # "aws_secret_access_key": "test_secret_access_key",
        # "aws_session_token": "test_session_token",
        # "aws_profile_name": "test_profile_name",
        # "aws_read_timeout": 120,
        # "aws_connect_timeout: 30,
        "model": "anthropic.claude-3-sonnet-20240229-v1:0",
        "temperature": 0.8,
        "topP": 0.6,
        "maxTokens": 250,
        "seed": 42,
        "stream": False,
    }
    expected_base_params = {
        "temperature": 0.8,
        "topP": 0.6,
        "maxTokens": 250,
    }
    expected_additional_params = {
        "seed": 42,
    }
    base_result, additional_result = bedrock_client.parse_params(params)
    assert base_result == expected_base_params
    assert additional_result == expected_additional_params

    # Incorrect types, defaults should be set, will show warnings but not trigger assertions
    params = {
        "model": "anthropic.claude-3-sonnet-20240229-v1:0",
        "temperature": "0.5",
        "topP": "0.6",
        "maxTokens": "250",
        "seed": "42",
        "stream": "False",
    }
    expected_base_params = {
        "temperature": None,
        "topP": None,
        "maxTokens": None,
    }
    expected_additional_params = {
        "seed": None,
    }
    base_result, additional_result = bedrock_client.parse_params(params)
    assert base_result == expected_base_params
    assert additional_result == expected_additional_params

    # Only model, others set as defaults if they are mandatory
    params = {
        "model": "anthropic.claude-3-sonnet-20240229-v1:0",
    }
    expected_base_params = {}
    expected_additional_params = {}
    base_result, additional_result = bedrock_client.parse_params(params)
    assert base_result == expected_base_params
    assert additional_result == expected_additional_params

    # No model
    params = {
        "temperature": 0.8,
    }

    with pytest.raises(AssertionError) as assertinfo:
        bedrock_client.parse_params(params)

    assert "Please provide the 'model` in the config_list to use Amazon Bedrock" in str(assertinfo.value)


# Test text generation
@pytest.mark.skipif(skip, reason=skip_reason)
@patch("autogen.oai.bedrock.BedrockClient.create")
def test_create_response(mock_chat, bedrock_client):
    # Mock BedrockClient.chat response
    mock_bedrock_response = MagicMock()
    mock_bedrock_response.choices = [
        MagicMock(finish_reason="stop", message=MagicMock(content="Example Bedrock response", tool_calls=None))
    ]
    mock_bedrock_response.id = "mock_bedrock_response_id"
    mock_bedrock_response.model = "anthropic.claude-3-sonnet-20240229-v1:0"
    mock_bedrock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)  # Example token usage

    mock_chat.return_value = mock_bedrock_response

    # Test parameters
    params = {
        "messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "World"}],
        "model": "anthropic.claude-3-sonnet-20240229-v1:0",
    }

    # Call the create method
    response = bedrock_client.create(params)

    # Assertions to check if response is structured as expected
    assert (
        response.choices[0].message.content == "Example Bedrock response"
    ), "Response content should match expected output"
    assert response.id == "mock_bedrock_response_id", "Response ID should match the mocked response ID"
    assert (
        response.model == "anthropic.claude-3-sonnet-20240229-v1:0"
    ), "Response model should match the mocked response model"
    assert response.usage.prompt_tokens == 10, "Response prompt tokens should match the mocked response usage"
    assert response.usage.completion_tokens == 20, "Response completion tokens should match the mocked response usage"


# Test functions/tools
@pytest.mark.skipif(skip, reason=skip_reason)
@patch("autogen.oai.bedrock.BedrockClient.create")
def test_create_response_with_tool_call(mock_chat, bedrock_client):
    # Mock BedrockClient.chat response
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
                        MagicMock(id="bd65600d-8669-4903-8a14-af88203add38", function=mock_function),
                        MagicMock(id="f50ec0b7-f960-400d-91f0-c42a6d44e3d0", function=mock_function_2),
                    ],
                ),
            )
        ],
        id="mock_bedrock_response_id",
        model="anthropic.claude-3-sonnet-20240229-v1:0",
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
    bedrock_messages = [
        {"role": "user", "content": "How much is 123.45 EUR in USD?"},
        {"role": "assistant", "content": "World"},
    ]

    # Call the create method
    response = bedrock_client.create(
        {"messages": bedrock_messages, "tools": converted_functions, "model": "anthropic.claude-3-sonnet-20240229-v1:0"}
    )

    # Assertions to check if the functions and content are included in the response
    assert response.choices[0].message.content == "Sample text about the functions"
    assert response.choices[0].message.tool_calls[0].function.name == "currency_calculator"
    assert response.choices[0].message.tool_calls[1].function.name == "get_weather"


# Test message conversion from OpenAI to Bedrock format
@pytest.mark.skipif(skip, reason=skip_reason)
def test_oai_messages_to_bedrock_messages(bedrock_client):

    # Test that the "name" key is removed and system messages converted to user message
    test_messages = [
        {"role": "system", "content": "You are a helpful AI bot."},
        {"role": "user", "name": "anne", "content": "Why is the sky blue?"},
    ]
    messages = oai_messages_to_bedrock_messages(test_messages, False, False)

    expected_messages = [
        {"role": "user", "content": [{"text": "You are a helpful AI bot."}]},
        {"role": "assistant", "content": [{"text": "Please continue."}]},
        {"role": "user", "content": [{"text": "Why is the sky blue?"}]},
    ]

    assert messages == expected_messages, "'name' was not removed from messages (system message should be user message)"

    # Test that the "name" key is removed and system messages are extracted (as they will be put in separately)
    test_messages = [
        {"role": "system", "content": "You are a helpful AI bot."},
        {"role": "user", "name": "anne", "content": "Why is the sky blue?"},
    ]
    messages = oai_messages_to_bedrock_messages(test_messages, False, True)

    expected_messages = [
        {"role": "user", "content": [{"text": "Why is the sky blue?"}]},
    ]

    assert messages == expected_messages, "'name' was not removed from messages (system messages excluded)"

    # Test that the system message is converted to user and that a continue message is inserted
    test_messages = [
        {"role": "system", "content": "You are a helpful AI bot."},
        {"role": "user", "name": "anne", "content": "Why is the sky blue?"},
        {"role": "system", "content": "Summarise the conversation."},
    ]

    messages = oai_messages_to_bedrock_messages(test_messages, False, False)

    expected_messages = [
        {"role": "user", "content": [{"text": "You are a helpful AI bot."}]},
        {"role": "assistant", "content": [{"text": "Please continue."}]},
        {"role": "user", "content": [{"text": "Why is the sky blue?"}]},
        {"role": "assistant", "content": [{"text": "Please continue."}]},
        {"role": "user", "content": [{"text": "Summarise the conversation."}]},
    ]

    assert (
        messages == expected_messages
    ), "Final 'system' message was not changed to 'user' or continue messages not included"

    # Test that the last message is a user or system message and if not, add a continue message
    test_messages = [
        {"role": "system", "content": "You are a helpful AI bot."},
        {"role": "user", "name": "anne", "content": "Why is the sky blue?"},
        {"role": "assistant", "content": "The sky is blue because that's a great colour."},
    ]
    print(test_messages)

    messages = oai_messages_to_bedrock_messages(test_messages, False, False)
    print(messages)

    expected_messages = [
        {"role": "user", "content": [{"text": "You are a helpful AI bot."}]},
        {"role": "assistant", "content": [{"text": "Please continue."}]},
        {"role": "user", "content": [{"text": "Why is the sky blue?"}]},
        {"role": "assistant", "content": [{"text": "The sky is blue because that's a great colour."}]},
        {"role": "user", "content": [{"text": "Please continue."}]},
    ]

    assert messages == expected_messages, "'Please continue' message was not appended."
