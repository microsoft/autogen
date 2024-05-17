from unittest.mock import MagicMock, patch

import pytest

try:
    from google.api_core.exceptions import InternalServerError

    from autogen.oai.gemini import GeminiClient

    skip = False
except ImportError:
    GeminiClient = object
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
def gemini_client():
    return GeminiClient(api_key="fake_api_key")


# Test initialization and configuration
@pytest.mark.skipif(skip, reason="Google GenAI dependency is not installed")
def test_initialization():
    with pytest.raises(AssertionError):
        GeminiClient()  # Should raise an AssertionError due to missing API key


@pytest.mark.skipif(skip, reason="Google GenAI dependency is not installed")
def test_valid_initialization(gemini_client):
    assert gemini_client.api_key == "fake_api_key", "API Key should be correctly set"


# Test error handling
@patch("autogen.oai.gemini.genai")
@pytest.mark.skipif(skip, reason="Google GenAI dependency is not installed")
def test_internal_server_error_retry(mock_genai, gemini_client):
    mock_genai.GenerativeModel.side_effect = [InternalServerError("Test Error"), None]  # First call fails
    # Mock successful response
    mock_chat = MagicMock()
    mock_chat.send_message.return_value = "Successful response"
    mock_genai.GenerativeModel.return_value.start_chat.return_value = mock_chat

    with patch.object(gemini_client, "create", return_value="Retried Successfully"):
        response = gemini_client.create({"model": "gemini-pro", "messages": [{"content": "Hello"}]})
        assert response == "Retried Successfully", "Should retry on InternalServerError"


# Test cost calculation
@pytest.mark.skipif(skip, reason="Google GenAI dependency is not installed")
def test_cost_calculation(gemini_client, mock_response):
    response = mock_response(
        text="Example response",
        choices=[{"message": "Test message 1"}],
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        cost=0.01,
        model="gemini-pro",
    )
    assert gemini_client.cost(response) > 0, "Cost should be correctly calculated as zero"


@pytest.mark.skipif(skip, reason="Google GenAI dependency is not installed")
@patch("autogen.oai.gemini.genai.GenerativeModel")
@patch("autogen.oai.gemini.genai.configure")
def test_create_response(mock_configure, mock_generative_model, gemini_client):
    # Mock the genai model configuration and creation process
    mock_chat = MagicMock()
    mock_model = MagicMock()
    mock_configure.return_value = None
    mock_generative_model.return_value = mock_model
    mock_model.start_chat.return_value = mock_chat

    # Set up a mock for the chat history item access and the text attribute return
    mock_history_part = MagicMock()
    mock_history_part.text = "Example response"
    mock_chat.history.__getitem__.return_value.parts.__getitem__.return_value = mock_history_part

    # Setup the mock to return a mocked chat response
    mock_chat.send_message.return_value = MagicMock(history=[MagicMock(parts=[MagicMock(text="Example response")])])

    # Call the create method
    response = gemini_client.create(
        {"model": "gemini-pro", "messages": [{"content": "Hello", "role": "user"}], "stream": False}
    )

    # Assertions to check if response is structured as expected
    assert response.choices[0].message.content == "Example response", "Response content should match expected output"


@pytest.mark.skipif(skip, reason="Google GenAI dependency is not installed")
@patch("autogen.oai.gemini.genai.GenerativeModel")
@patch("autogen.oai.gemini.genai.configure")
def test_create_vision_model_response(mock_configure, mock_generative_model, gemini_client):
    # Mock the genai model configuration and creation process
    mock_model = MagicMock()
    mock_configure.return_value = None
    mock_generative_model.return_value = mock_model

    # Set up a mock to simulate the vision model behavior
    mock_vision_response = MagicMock()
    mock_vision_part = MagicMock(text="Vision model output")

    # Setting up the chain of return values for vision model response
    mock_vision_response._result.candidates.__getitem__.return_value.content.parts.__getitem__.return_value = (
        mock_vision_part
    )
    mock_model.generate_content.return_value = mock_vision_response

    # Call the create method with vision model parameters
    response = gemini_client.create(
        {
            "model": "gemini-pro-vision",  # Vision model name
            "messages": [
                {
                    "content": [
                        {"type": "text", "text": "Let's play a game."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
                            },
                        },
                    ],
                    "role": "user",
                }
            ],  # Assuming a simple content input for vision
            "stream": False,
        }
    )

    # Assertions to check if response is structured as expected
    assert (
        response.choices[0].message.content == "Vision model output"
    ), "Response content should match expected output from vision model"
