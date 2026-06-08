"""Tests for Azure AI Search tool."""

import asyncio
from collections.abc import Generator
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import CancellationToken
from autogen_ext.tools.azure import (
    AzureAISearchConfig,
    AzureAISearchTool,
    SearchResult,
    SearchResults,
)
from autogen_ext.tools.azure._ai_search import BaseAzureAISearchTool
from autogen_ext.tools.azure._config import DEFAULT_API_VERSION
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from pydantic import BaseModel, Field, ValidationError

MOCK_ENDPOINT = "https://test-search.search.windows.net"
MOCK_INDEX = "test-index"
MOCK_API_KEY = "test-key"
MOCK_CREDENTIAL = AzureKeyCredential(MOCK_API_KEY)


class MockAsyncTokenCredential(AsyncTokenCredential):
    """Mock async token credential for testing."""

    async def get_token(self, *scopes: str, **kwargs: Any) -> Any:
        return "mock-token"

    async def close(self) -> None:
        pass

    async def __aexit__(self, exc_type: Any = None, exc_val: Any = None, exc_tb: Any = None) -> None:
        await self.close()


@pytest.fixture
def search_config() -> AzureAISearchConfig:
    """Fixture for basic search configuration."""
    return AzureAISearchConfig(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        description="Test search tool",
    )


@pytest.fixture
def mock_search_client() -> Generator[AsyncMock, None, None]:
    """Fixture for mocked search client."""
    with patch("azure.search.documents.aio.SearchClient", autospec=True) as mock:
        mock_client = AsyncMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_search_results() -> List[Dict[str, Any]]:
    """Fixture for mock search results."""
    return [
        {
            "id": "1",
            "content": "Test content",
            "@search.score": 0.8,
        }
    ]


class TestSearchQuery(BaseModel):
    """Test model for query validation."""

    query: str = Field(min_length=1)


@pytest.mark.asyncio
async def test_search_query_model() -> None:
    """Test SearchQuery model validation."""
    query = TestSearchQuery(query="test query")
    assert query.query == "test query"

    with pytest.raises(ValidationError):
        TestSearchQuery(query="")


@pytest.mark.asyncio
async def test_search_result_model() -> None:
    """Test SearchResult model."""
    result = SearchResult(score=0.8, content={"title": "Test", "text": "Content"}, metadata={"@search.score": 0.8})
    assert result.score == 0.8
    assert result.content["title"] == "Test"
    assert result.metadata["@search.score"] == 0.8


@pytest.mark.asyncio
async def test_search_results_model() -> None:
    """Test SearchResults model."""
    results = SearchResults(
        results=[
            SearchResult(score=0.8, content={"title": "Test1"}, metadata={"@search.score": 0.8}),
            SearchResult(score=0.6, content={"title": "Test2"}, metadata={"@search.score": 0.6}),
        ]
    )
    assert len(results.results) == 2
    assert results.results[0].score == 0.8
    assert results.results[1].content["title"] == "Test2"


@pytest.mark.asyncio
async def test_create_full_text_search() -> None:
    """Test creation of full text search tool."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        search_fields=["content"],
        query_type="simple",
    )
    assert tool.name == "test-search"
    assert tool.search_config.query_type == "simple"
    assert tool.search_config.search_fields == ["content"]

    with pytest.raises(ValueError, match="semantic_config_name is required"):
        AzureAISearchTool.create_full_text_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential=MOCK_CREDENTIAL,
            query_type="semantic",
        )

    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        query_type="semantic",
        semantic_config_name="default",
    )
    assert tool.search_config.query_type == "semantic"
    assert tool.search_config.semantic_config_name == "default"


@pytest.mark.asyncio
async def test_create_vector_search() -> None:
    """Test creation of vector search tool."""
    tool = AzureAISearchTool.create_vector_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        vector_fields=["embedding"],
    )
    assert tool.search_config.query_type == "vector"
    assert tool.search_config.vector_fields == ["embedding"]

    with pytest.raises(ValueError, match="openai_endpoint is required"):
        AzureAISearchTool.create_vector_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential=MOCK_CREDENTIAL,
            vector_fields=["embedding"],
            embedding_provider="azure_openai",
            embedding_model="text-embedding-ada-002",
        )


@pytest.mark.asyncio
async def test_create_hybrid_search() -> None:
    """Test creation of hybrid search tool."""
    tool = AzureAISearchTool.create_hybrid_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        vector_fields=["embedding"],
        search_fields=["content"],
    )
    assert tool.search_config.vector_fields == ["embedding"]
    assert tool.search_config.search_fields == ["content"]

    tool = AzureAISearchTool.create_hybrid_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        vector_fields=["embedding"],
        search_fields=["content"],
        query_type="semantic",
        semantic_config_name="default",
    )
    assert tool.search_config.query_type == "semantic"
    assert tool.search_config.semantic_config_name == "default"


@pytest.mark.asyncio
async def test_search_execution(mock_search_client: AsyncMock, mock_search_results: List[Dict[str, Any]]) -> None:
    """Test search execution with mocked client."""
    mock_search_client.search.return_value.__aiter__.return_value = mock_search_results

    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    with patch.object(tool, "_get_client", return_value=mock_search_client):
        results = await tool.run("test query")

        assert len(results.results) == 1
        assert results.results[0].score == 0.8
        assert results.results[0].content["content"] == "Test content"

        mock_search_client.search.assert_called_once()
        call_kwargs = mock_search_client.search.call_args[1]
        assert call_kwargs["search_text"] == "test query"


@pytest.mark.asyncio
async def test_search_with_caching(mock_search_client: AsyncMock, mock_search_results: List[Dict[str, Any]]) -> None:
    """Test search caching functionality."""
    mock_search_client.search.return_value.__aiter__.return_value = mock_search_results

    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        enable_caching=True,
        cache_ttl_seconds=300,
    )

    with patch.object(tool, "_get_client", return_value=mock_search_client):
        await tool.run("test query")
        assert mock_search_client.search.call_count == 1

        await tool.run("test query")
        assert mock_search_client.search.call_count == 1


@pytest.mark.asyncio
async def test_error_handling(mock_search_client: AsyncMock) -> None:
    """Test error handling in search execution."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    with patch.object(tool, "_get_client", return_value=mock_search_client):
        mock_search_client.search.side_effect = ResourceNotFoundError("Index not found")
        with pytest.raises(ValueError, match="Index.*not found"):
            await tool.run("test query")

        mock_search_client.search.side_effect = HttpResponseError(status_code=401, message="Unauthorized")
        with pytest.raises(ValueError, match="Authentication failed"):
            await tool.run("test query")

        mock_search_client.search.side_effect = HttpResponseError(status_code=500, message="Internal server error")
        with pytest.raises(ValueError, match="Error from Azure AI Search"):
            await tool.run("test query")


@pytest.mark.asyncio
async def test_embedding_provider_mixin() -> None:
    """Test the embedding provider functionality."""
    with patch("openai.AsyncAzureOpenAI") as mock_azure_openai:
        mock_client = AsyncMock()
        mock_azure_openai.return_value = mock_client
        mock_client.embeddings.create.return_value.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]

        tool = AzureAISearchTool.create_vector_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential=MOCK_CREDENTIAL,
            vector_fields=["embedding"],
            embedding_provider="azure_openai",
            embedding_model="text-embedding-ada-002",
            openai_endpoint="https://test.openai.azure.com",
            openai_api_key="test-key",
        )

        embedding = await tool._get_embedding("test query")  # pyright: ignore[reportPrivateUsage]
        assert len(embedding) == 3
        assert embedding == [0.1, 0.2, 0.3]

        mock_client.embeddings.create.assert_called_once_with(model="text-embedding-ada-002", input="test query")


@pytest.mark.asyncio
async def test_credential_processing() -> None:
    """Test credential processing logic."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )
    assert isinstance(tool.search_config.credential, AzureKeyCredential)
    assert tool.search_config.credential.key == MOCK_API_KEY

    mock_async_credential = MockAsyncTokenCredential()
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=mock_async_credential,
    )
    assert isinstance(tool.search_config.credential, AsyncTokenCredential)

    with pytest.raises(ValueError, match="Invalid configuration"):
        AzureAISearchTool.create_full_text_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential={"api_key": "test-key"},  # type: ignore
        )


@pytest.mark.asyncio
async def test_return_value_as_string() -> None:
    """Test the string representation of search results."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    results = SearchResults(
        results=[
            SearchResult(score=0.8, content={"title": "Test1", "text": "Content1"}, metadata={"@search.score": 0.8}),
            SearchResult(score=0.6, content={"title": "Test2", "text": "Content2"}, metadata={"@search.score": 0.6}),
        ]
    )
    result_str = tool.return_value_as_string(results)
    assert "Result 1 (Score: 0.80)" in result_str
    assert "Result 2 (Score: 0.60)" in result_str
    assert "Test1" in result_str
    assert "Content2" in result_str

    empty_results = SearchResults(results=[])
    assert tool.return_value_as_string(empty_results) == "No results found."


@pytest.mark.asyncio
async def test_schema() -> None:
    """Test tool schema generation."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    schema = tool.schema
    assert schema["name"] == "test-search"
    assert "description" in schema
    assert "parameters" in schema
    assert "required" in schema["parameters"]
    assert schema["parameters"]["type"] == "object"
    assert "query" in schema["parameters"]["properties"]
    assert schema["parameters"]["required"] == ["query"]


@pytest.mark.asyncio
async def test_vector_search_execution(
    mock_search_client: AsyncMock, mock_search_results: List[Dict[str, Any]]
) -> None:
    """Test vector search execution."""
    mock_search_client.search.return_value.__aiter__.return_value = mock_search_results

    tool = AzureAISearchTool.create_vector_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        vector_fields=["embedding"],
        embedding_provider="azure_openai",
        embedding_model="text-embedding-ada-002",
        openai_endpoint="https://test.openai.azure.com",
        openai_api_key="test-key",
    )

    mock_embedding = [0.1, 0.2, 0.3]
    with (
        patch.object(tool, "_get_embedding", return_value=mock_embedding),
        patch.object(tool, "_get_client", return_value=mock_search_client),
    ):
        results = await tool.run("test query")
        assert len(results.results) == 1
        mock_search_client.search.assert_called_once()


@pytest.mark.asyncio
async def test_cancellation() -> None:
    """Test search cancellation."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    token = CancellationToken()
    token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tool.run("test query", cancellation_token=token)


@pytest.mark.asyncio
async def test_invalid_query_format() -> None:
    """Test invalid query format handling."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    with pytest.raises(ValueError, match="Invalid search query format"):
        await tool.run({"invalid": "format"})


@pytest.mark.asyncio
async def test_client_cleanup() -> None:
    """Test client cleanup."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    mock_client = AsyncMock()
    tool._client = mock_client  # pyright: ignore[reportPrivateUsage]
    await tool.close()

    mock_client.close.assert_called_once()
    assert tool._client is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_config_validation() -> None:
    """Test configuration validation."""
    with pytest.raises(ValueError, match="vector_fields must contain at least one field"):
        AzureAISearchTool._validate_config(  # pyright: ignore[reportPrivateUsage]
            {
                "name": "test-search",
                "endpoint": MOCK_ENDPOINT,
                "index_name": MOCK_INDEX,
                "credential": MOCK_CREDENTIAL,
            },
            "vector",
        )

    with pytest.raises(ValueError, match="vector_fields must contain at least one field"):
        AzureAISearchTool._validate_config(  # pyright: ignore[reportPrivateUsage]
            {
                "name": "test-search",
                "endpoint": MOCK_ENDPOINT,
                "index_name": MOCK_INDEX,
                "credential": MOCK_CREDENTIAL,
                "search_fields": ["content"],
            },
            "hybrid",
        )


@pytest.mark.asyncio
async def test_openai_embedding_provider() -> None:
    """Test OpenAI embedding provider."""
    with patch("openai.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        mock_client.embeddings.create.return_value.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]

        tool = AzureAISearchTool.create_vector_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential=MOCK_CREDENTIAL,
            vector_fields=["embedding"],
            embedding_provider="openai",
            embedding_model="text-embedding-ada-002",
            openai_api_key="test-key",
        )

        embedding = await tool._get_embedding("test query")  # pyright: ignore[reportPrivateUsage]
        assert len(embedding) == 3
        assert embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_embedding_provider_error_handling() -> None:
    """Test error handling in embedding providers."""
    with pytest.raises(ValueError, match="openai_endpoint is required when embedding_provider is 'azure_openai'"):
        AzureAISearchTool.create_vector_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential=MOCK_CREDENTIAL,
            vector_fields=["embedding"],
            embedding_provider="azure_openai",
            embedding_model="text-embedding-ada-002",
            openai_api_version="2023-11-01",
        )

    tool = AzureAISearchTool.create_vector_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        vector_fields=["embedding"],
        embedding_provider="azure_openai",
        embedding_model="text-embedding-ada-002",
        openai_endpoint="https://test.openai.azure.com",
        openai_api_version="2023-11-01",
    )
    with patch("azure.identity.DefaultAzureCredential") as mock_credential:
        mock_credential.return_value.get_token.return_value = None
        with pytest.raises(ValueError, match="Failed to acquire token using DefaultAzureCredential for Azure OpenAI"):
            await tool._get_embedding("test query")  # pyright: ignore[reportPrivateUsage]

    tool = AzureAISearchTool.create_vector_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        vector_fields=["embedding"],
        embedding_provider="unsupported_provider",
        embedding_model="test-model",
    )
    with pytest.raises(ValueError, match="Unsupported client-side embedding provider: unsupported_provider"):
        await tool._get_embedding("test query")  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_abstract_base_class() -> None:
    """Test abstract base class behavior."""
    with pytest.raises(NotImplementedError):
        BaseAzureAISearchTool._from_config(  # pyright: ignore[reportPrivateUsage]
            AzureAISearchConfig(
                name="test",
                endpoint=MOCK_ENDPOINT,
                index_name=MOCK_INDEX,
                credential=MOCK_CREDENTIAL,
            )
        )


@pytest.mark.asyncio
async def test_client_initialization_errors() -> None:
    """Test client initialization error handling."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    with patch("azure.search.documents.aio.SearchClient.__init__", side_effect=Exception("Connection error")):
        with pytest.raises(ValueError, match="Unexpected error initializing search client: Connection error"):
            await tool._get_client()  # pyright: ignore[reportPrivateUsage]

    with patch(
        "azure.search.documents.aio.SearchClient.__init__", side_effect=ResourceNotFoundError("Index not found")
    ):
        with pytest.raises(ValueError, match=f"Index '{MOCK_INDEX}' not found"):
            await tool._get_client()  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_client_initialization_with_error() -> None:
    """Test client initialization with various errors."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    class MockResponse:
        def __init__(self, status_code: int, reason: str):
            self.status_code = status_code
            self.reason = reason
            self.request = object()

        def text(self) -> str:
            return f"{self.status_code} {self.reason}"

    mock_response = MockResponse(status_code=401, reason="Unauthorized")
    with patch(
        "azure.search.documents.aio.SearchClient.__init__", side_effect=HttpResponseError(response=mock_response)
    ):
        with pytest.raises(ValueError, match="Authentication failed"):
            await tool._get_client()  # pyright: ignore[reportPrivateUsage]

    mock_response = MockResponse(status_code=403, reason="Forbidden")
    with patch(
        "azure.search.documents.aio.SearchClient.__init__", side_effect=HttpResponseError(response=mock_response)
    ):
        with pytest.raises(ValueError, match="Permission denied"):
            await tool._get_client()  # pyright: ignore[reportPrivateUsage]

    mock_response = MockResponse(status_code=500, reason="Internal Server Error")
    with patch(
        "azure.search.documents.aio.SearchClient.__init__", side_effect=HttpResponseError(response=mock_response)
    ):
        with pytest.raises(ValueError, match="Error connecting to Azure AI Search"):
            await tool._get_client()  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_search_document_processing_error(mock_search_client: AsyncMock) -> None:
    """Test error handling during search document processing."""
    mock_search_client.search.return_value.__aiter__.return_value = [{"invalid": "document", "@search.score": None}]

    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    with patch.object(tool, "_get_client", return_value=mock_search_client):
        results = await tool.run("test query")
        assert len(results.results) == 0


@pytest.mark.asyncio
async def test_search_with_expired_cache(
    mock_search_client: AsyncMock, mock_search_results: List[Dict[str, Any]]
) -> None:
    """Test search with expired cache."""
    mock_search_client.search.return_value.__aiter__.return_value = mock_search_results

    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        enable_caching=True,
        cache_ttl_seconds=1,
    )

    with patch.object(tool, "_get_client", return_value=mock_search_client):
        await tool.run("test query")
        assert mock_search_client.search.call_count == 1

        await asyncio.sleep(1.1)

        await tool.run("test query")
        assert mock_search_client.search.call_count == 2


@pytest.mark.asyncio
async def test_search_with_invalid_credential() -> None:
    """Test search with invalid credential format."""
    with pytest.raises(ValueError, match="Invalid configuration"):
        AzureAISearchTool.create_full_text_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential={"api_key": "test-key"},  # type: ignore
        )


@pytest.mark.asyncio
async def test_search_with_empty_query() -> None:
    """Test search with empty query."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    with pytest.raises(ValueError, match="Search query cannot be empty"):
        await tool.run("")


@pytest.mark.asyncio
async def test_vector_search_without_query() -> None:
    """Test vector search with empty query."""
    tool = AzureAISearchTool.create_vector_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        vector_fields=["embedding"],
    )

    with pytest.raises(ValueError, match="Search query cannot be empty"):
        await tool.run("")


@pytest.mark.asyncio
async def test_search_with_cancellation_token_already_cancelled() -> None:
    """Test search with already cancelled token."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    token = CancellationToken()
    token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await tool.run("test query", cancellation_token=token)


@pytest.mark.asyncio
async def test_config_validation_edge_cases() -> None:
    """Test configuration validation edge cases."""
    with pytest.raises(
        ValueError,
        match="Invalid configuration: 1 validation error for AzureAISearchConfig\n  Value error, vector_fields must be provided for vector search",
    ):
        AzureAISearchTool.create_vector_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential=MOCK_CREDENTIAL,
            vector_fields=[],
        )

    with pytest.raises(ValueError, match="vector_fields must contain at least one field name for hybrid search"):
        AzureAISearchTool.create_hybrid_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential=MOCK_CREDENTIAL,
            vector_fields=[],
            search_fields=["content"],
        )

    with pytest.raises(ValueError, match="semantic_config_name is required when query_type is 'semantic'"):
        AzureAISearchTool.create_hybrid_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential=MOCK_CREDENTIAL,
            vector_fields=["embedding"],
            search_fields=["content"],
            query_type="semantic",
        )


@pytest.mark.asyncio
async def test_base_class_functionality() -> None:
    """Test base class functionality."""
    config = AzureAISearchConfig(
        name="test",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    with pytest.raises(NotImplementedError, match="BaseAzureAISearchTool.*cannot be instantiated directly"):
        BaseAzureAISearchTool._from_config(config)  # pyright: ignore[reportPrivateUsage]

    class TestSearchTool(BaseAzureAISearchTool):
        async def _get_embedding(self, query: str) -> List[float]:
            return [0.1, 0.2, 0.3]

        @classmethod
        def _from_config(cls, config: AzureAISearchConfig) -> "TestSearchTool":
            return cls(
                name=config.name,
                endpoint=config.endpoint,
                index_name=config.index_name,
                credential=config.credential,
            )

    tool = TestSearchTool._from_config(config)  # pyright: ignore[reportPrivateUsage]
    assert tool.name == "test"
    assert tool.search_config.endpoint == MOCK_ENDPOINT


@pytest.mark.asyncio
async def test_client_cleanup_edge_cases() -> None:
    """Test client cleanup edge cases."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
    )

    tool._client = None  # pyright: ignore[reportPrivateUsage]
    await tool.close()

    mock_client = AsyncMock()
    mock_client.close.side_effect = Exception("Failed to close")
    tool._client = mock_client  # pyright: ignore[reportPrivateUsage]
    await tool.close()
    assert tool._client is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_token_acquisition_edge_cases() -> None:
    """Test token acquisition edge cases."""
    with patch("azure.identity.DefaultAzureCredential") as mock_credential:
        mock_credential.return_value.get_token.return_value = None

        tool = AzureAISearchTool.create_vector_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential=MOCK_CREDENTIAL,
            vector_fields=["embedding"],
            embedding_provider="azure_openai",
            embedding_model="text-embedding-ada-002",
            openai_endpoint="https://test.openai.azure.com",
            openai_api_version="2023-11-01",
        )

        with pytest.raises(ValueError, match="Failed to acquire token using DefaultAzureCredential for Azure OpenAI"):
            await tool._get_embedding("test query")  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_hybrid_search_validation() -> None:
    """Test hybrid search validation edge cases."""
    with pytest.raises(ValueError, match="semantic_config_name is required when query_type is 'semantic'"):
        AzureAISearchTool.create_hybrid_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential=MOCK_CREDENTIAL,
            vector_fields=["embedding"],
            search_fields=["content"],
            query_type="semantic",
        )

    with pytest.raises(ValueError, match="openai_endpoint is required when embedding_provider is 'azure_openai'"):
        AzureAISearchTool.create_hybrid_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential=MOCK_CREDENTIAL,
            vector_fields=["embedding"],
            search_fields=["content"],
            embedding_provider="azure_openai",
            embedding_model="text-embedding-ada-002",
        )


@pytest.mark.asyncio
async def test_search_result_caching() -> None:
    """Test that search results are properly cached and retrieved."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        enable_caching=True,
        cache_ttl_seconds=10,
    )

    mock_results = [{"id": "1", "content": "Test", "@search.score": 0.8}]

    with patch.object(tool, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.search.return_value.__aiter__.return_value = mock_results
        mock_get_client.return_value = mock_client

        result1 = await tool.run("test query")
        assert len(result1.results) == 1
        assert mock_client.search.call_count == 1

        result2 = await tool.run("test query")
        assert len(result2.results) == 1
        assert mock_client.search.call_count == 1


@pytest.mark.asyncio
async def test_cache_expiration() -> None:
    """Test that cached results expire after TTL."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        enable_caching=True,
        cache_ttl_seconds=1,
    )

    mock_results = [{"id": "1", "content": "Test", "@search.score": 0.8}]

    with patch.object(tool, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.search.return_value.__aiter__.return_value = mock_results
        mock_get_client.return_value = mock_client

        await tool.run("test query")
        assert mock_client.search.call_count == 1

        await asyncio.sleep(1.1)

        await tool.run("test query")
        assert mock_client.search.call_count == 2


@pytest.mark.asyncio
async def test_search_field_validation() -> None:
    """Test validation of search fields configuration."""
    tool = AzureAISearchTool.create_full_text_search(
        name="test-search", endpoint=MOCK_ENDPOINT, index_name=MOCK_INDEX, credential=MOCK_CREDENTIAL, search_fields=[]
    )
    assert tool.search_config.search_fields == []

    tool = AzureAISearchTool.create_full_text_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        search_fields=["content", "content"],
    )
    assert tool.search_config.search_fields == ["content", "content"]


@pytest.mark.asyncio
async def test_api_version_handling() -> None:
    """Test handling of different API versions."""
    tool = AzureAISearchTool.create_vector_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        vector_fields=["embedding"],
        api_version="2023-11-01",
    )
    assert tool.search_config.api_version == "2023-11-01"

    tool = AzureAISearchTool.create_vector_search(
        name="test-search",
        endpoint=MOCK_ENDPOINT,
        index_name=MOCK_INDEX,
        credential=MOCK_CREDENTIAL,
        vector_fields=["embedding"],
    )
    assert tool.search_config.api_version == DEFAULT_API_VERSION

    with patch("autogen_ext.tools.azure._ai_search.logger") as mock_logger:
        AzureAISearchTool.create_vector_search(
            name="test-search",
            endpoint=MOCK_ENDPOINT,
            index_name=MOCK_INDEX,
            credential=MOCK_CREDENTIAL,
            vector_fields=["embedding"],
            api_version="2023-11-01",
        )

        mock_logger.warning.assert_called_once()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "vector search" in warning_msg.lower()
        assert "2023-11-01" in warning_msg
