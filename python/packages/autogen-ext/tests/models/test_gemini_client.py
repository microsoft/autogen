import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_ext.models.gemini import (
    GeminiChatCompletionClient,
    VertexAIChatCompletionClient,
)
from pydantic import ValidationError


@pytest.fixture
def mock_genai():
    with patch("google.genai") as mock:
        # Setup basic client mock
        mock.Client = MagicMock()
        mock_client = mock.Client.return_value

        # Setup async client
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock()

        # Setup sync client for token counting
        mock_client.models = MagicMock()
        mock_client.models.count_tokens = MagicMock()
        mock_client.models.count_tokens.return_value = MagicMock(total_tokens=10)
        mock_client.models.generate_content = MagicMock()

        # Setup types
        mock.types = MagicMock()
        mock.types.Content = MagicMock()
        mock.types.Part = MagicMock()
        mock.types.Part.from_text = MagicMock(return_value=MagicMock())
        mock.types.Part.from_data = MagicMock(return_value=MagicMock())
        mock.types.Tool = MagicMock()
        mock.types.FunctionDeclaration = MagicMock()
        mock.types.Schema = MagicMock()
        mock.types.Schema.from_dict = MagicMock(return_value=MagicMock())

        # Setup error types
        mock.errors = MagicMock()
        mock.errors.ClientError = Exception

        yield mock


@pytest.fixture
def mock_aiplatform():
    with patch("google.cloud.aiplatform", create=True) as mock:
        mock.init = MagicMock()
        yield mock


@pytest.fixture
def mock_response():
    response = MagicMock()
    response.text = "Test response"
    response.usage_metadata = MagicMock()
    response.usage_metadata.prompt_token_count = 10
    response.usage_metadata.candidates_token_count = 20
    response.candidates = [MagicMock()]
    response.candidates[0].content = MagicMock()
    response.candidates[0].content.parts = [MagicMock()]
    response.candidates[0].content.parts[0].text = "Test response"
    response.candidates[0].content.parts[0].function_call = None
    response.candidates[0].finish_reason = "stop"
    return response


@pytest.fixture
def mock_function_response():
    response = MagicMock()
    response.text = ""
    response.usage_metadata = MagicMock()
    response.usage_metadata.prompt_token_count = 10
    response.usage_metadata.candidates_token_count = 20

    # Setup function call response
    response.candidates = [MagicMock()]
    response.candidates[0].content = MagicMock()
    response.candidates[0].content.parts = [MagicMock()]
    response.candidates[0].content.parts[0].text = ""

    # Create a function call mock with a proper name attribute
    function_call = MagicMock()
    function_call.name = "test_function"
    function_call.args = {"arg1": "value1"}
    response.candidates[0].content.parts[0].function_call = function_call
    response.candidates[0].finish_reason = "function_calls"

    return response


@pytest.fixture
def mock_stream_response():
    response = MagicMock()
    response.text = "This is a test response that will be streamed in chunks"
    response.usage_metadata = MagicMock()
    response.usage_metadata.prompt_token_count = 10
    response.usage_metadata.candidates_token_count = 20
    response.candidates = [MagicMock()]
    response.candidates[0].content = MagicMock()
    response.candidates[0].content.parts = [MagicMock()]
    response.candidates[0].content.parts[0].text = response.text
    response.candidates[0].content.parts[0].function_call = None
    response.candidates[0].finish_reason = "stop"
    return response


@pytest.fixture
def gemini_client(mock_genai):
    client = GeminiChatCompletionClient(
        model="gemini-1.5-pro",
        api_key="test-api-key",
    )
    client._client = mock_genai.Client()
    return client


@pytest.fixture
def vertex_client(mock_genai, mock_aiplatform):
    with patch.dict(os.environ, {
        "GOOGLE_GENAI_USE_VERTEXAI": "1",
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
    }):
        client = VertexAIChatCompletionClient(
            model="gemini-1.5-pro",
            project_id="test-project",
            location="us-central1",
        )
        client._client = mock_genai.Client()
        return client


@pytest.mark.asyncio
async def test_gemini_create(gemini_client, mock_genai, mock_response):
    mock_genai.Client.return_value.aio.models.generate_content.return_value = mock_response

    messages = [
        SystemMessage(content="You are a helpful assistant.", source="system"),
        UserMessage(content="Hello!", source="user"),
        AssistantMessage(content="Hi there!", source="assistant"),
    ]

    result = await gemini_client.create(messages)

    assert isinstance(result, CreateResult)
    assert result.content == "Test response"
    assert result.finish_reason == "stop"
    assert result.usage.prompt_tokens == 10
    assert result.usage.completion_tokens == 20


@pytest.mark.asyncio
async def test_gemini_create_stream(gemini_client, mock_genai, mock_stream_response):
    mock_genai.Client.return_value.aio.models.generate_content.return_value = mock_stream_response

    messages = [
        UserMessage(content="Hello!", source="user"),
    ]

    chunks = []
    async for chunk in gemini_client.create_stream(messages):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert "".join(chunks) == mock_stream_response.text


@pytest.mark.asyncio
async def test_vertex_create(vertex_client, mock_genai, mock_aiplatform, mock_response):
    mock_genai.Client.return_value.aio.models.generate_content.return_value = mock_response

    messages = [
        UserMessage(content="Hello!", source="user"),
    ]

    result = await vertex_client.create(messages)

    assert isinstance(result, CreateResult)
    assert result.content == "Test response"
    assert result.finish_reason == "stop"
    assert result.usage.prompt_tokens == 10
    assert result.usage.completion_tokens == 20

    mock_aiplatform.init.assert_called_once_with(
        project="test-project",
        location="us-central1",
        credentials=None,
    )


def test_gemini_client_init_no_api_key():
    with pytest.raises(ValidationError) as exc_info:
        GeminiChatCompletionClient(model="gemini-1.5-pro")
    assert "api_key" in str(exc_info.value)


def test_vertex_client_init_no_project():
    with pytest.raises(ValidationError) as exc_info:
        VertexAIChatCompletionClient(model="gemini-1.5-pro")
    assert "project_id" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gemini_create_with_tools(gemini_client, mock_genai, mock_function_response):
    mock_genai.Client.return_value.aio.models.generate_content.return_value = mock_function_response

    messages = [UserMessage(content="Call the test function", source="user")]
    tools = [{
        "name": "test_function",
        "description": "A test function",
        "parameters": {
            "type": "object",
            "properties": {
                "arg1": {"type": "string"}
            }
        }
    }]

    result = await gemini_client.create(messages, tools=tools)

    assert isinstance(result, CreateResult)
    assert result.finish_reason == "function_calls"
    assert isinstance(result.content, list)
    assert len(result.content) == 1
    assert result.content[0].name == "test_function"
    assert result.content[0].arguments == '{"arg1": "value1"}'


@pytest.mark.asyncio
async def test_gemini_error_handling(gemini_client, mock_genai):
    error = Exception("Test error")
    mock_genai.Client.return_value.aio.models.generate_content.side_effect = error

    messages = [UserMessage(content="Hello!", source="user")]

    with pytest.raises(Exception) as exc_info:
        async for _ in gemini_client.create_stream(messages):
            pass

    assert "Test error" in str(exc_info.value)


def test_client_capabilities(gemini_client, vertex_client):
    for client in [gemini_client, vertex_client]:
        capabilities = client.capabilities()
        assert isinstance(capabilities, dict)
        assert capabilities["stream"] is True
        assert capabilities["tools"] is True
        assert capabilities["vision"] is True
        assert capabilities["json_output"] is True
        assert capabilities["function_calling"] is True
        assert capabilities["async_agentic"] is True
