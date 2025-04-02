"""Tests for the Azure AI Search tool."""

from typing import Any, AsyncGenerator, Dict, List, cast
from unittest.mock import AsyncMock, patch

import pytest
from autogen_core import CancellationToken
from autogen_ext.tools.azure._ai_search import (
    AzureAISearchTool,
    SearchResult,
    SearchResults,
    _allow_private_constructor,  # pyright: ignore[reportPrivateUsage]
)
from azure.core.credentials import AzureKeyCredential, TokenCredential


@pytest.fixture
async def search_tool() -> AsyncGenerator[AzureAISearchTool, None]:
    """Create a concrete search tool for testing."""

    class ConcreteSearchTool(AzureAISearchTool):
        async def _get_embedding(self, query: str) -> List[float]:
            return [0.1, 0.2, 0.3]

    token = _allow_private_constructor.set(True)  # pyright: ignore[reportPrivateUsage]
    try:
        tool = ConcreteSearchTool(
            name="test-search",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential=cast(TokenCredential, AzureKeyCredential("test-key")),
            query_type="keyword",
            search_fields=["title", "content"],
            select_fields=["title", "content"],
            top=10,
        )
        yield tool
    finally:
        _allow_private_constructor.reset(token)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_search_tool_run(search_tool: AsyncGenerator[AzureAISearchTool, None]) -> None:
    """Test the run method of the search tool."""
    tool = await anext(search_tool)
    query = "test query"
    cancellation_token = CancellationToken()

    class AsyncIterableMock:
        def __init__(self, items: List[Dict[str, Any]]) -> None:
            self._items = items

        def __aiter__(self) -> "AsyncIterableMock":
            return self

        async def __anext__(self) -> Dict[str, Any]:
            if not self._items:
                raise StopAsyncIteration
            return self._items.pop(0)

    with patch.object(tool, "_get_client", AsyncMock()) as mock_client:
        mock_client.return_value.search = AsyncMock(
            return_value=AsyncIterableMock([{"@search.score": 0.95, "title": "Test Doc", "content": "Test Content"}])
        )

        results = await tool.run(query, cancellation_token)
        assert isinstance(results, SearchResults)
        assert len(results.results) == 1
        assert results.results[0].content["title"] == "Test Doc"
        assert results.results[0].score == 0.95


@pytest.mark.asyncio
async def test_search_tool_error_handling(search_tool: AsyncGenerator[AzureAISearchTool, None]) -> None:
    """Test error handling in the search tool."""
    tool = await anext(search_tool)
    with patch.object(tool, "_get_client", AsyncMock()) as mock_client:
        mock_client.return_value.search = AsyncMock(side_effect=ValueError("Test error"))

        with pytest.raises(ValueError, match="Test error"):
            await tool.run("test query", CancellationToken())


@pytest.mark.asyncio
async def test_search_tool_cancellation(search_tool: AsyncGenerator[AzureAISearchTool, None]) -> None:
    """Test cancellation of the search tool."""
    tool = await anext(search_tool)
    cancellation_token = CancellationToken()
    cancellation_token.cancel()

    with pytest.raises(ValueError, match="cancelled"):
        await tool.run("test query", cancellation_token)


@pytest.mark.asyncio
async def test_search_tool_vector_search() -> None:
    """Test vector search functionality."""

    class ConcreteSearchTool(AzureAISearchTool):
        async def _get_embedding(self, query: str) -> List[float]:
            return [0.1, 0.2, 0.3]

    token = _allow_private_constructor.set(True)  # pyright: ignore[reportPrivateUsage]
    try:
        tool = ConcreteSearchTool(
            name="vector-search",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential=cast(TokenCredential, AzureKeyCredential("test-key")),
            query_type="vector",
            vector_fields=["embedding"],
            select_fields=["title", "content"],
            top=10,
        )

        class AsyncIterableMock:
            def __init__(self, items: List[Dict[str, Any]]) -> None:
                self._items = items

            def __aiter__(self) -> "AsyncIterableMock":
                return self

            async def __anext__(self) -> Dict[str, Any]:
                if not self._items:
                    raise StopAsyncIteration
                return self._items.pop(0)

        with patch.object(tool, "_get_client", AsyncMock()) as mock_client:
            mock_client.return_value.search = AsyncMock(
                return_value=AsyncIterableMock(
                    [{"@search.score": 0.95, "title": "Vector Doc", "content": "Vector Content"}]
                )
            )

            results = await tool.run("vector query", CancellationToken())
            assert len(results.results) == 1
            assert results.results[0].content["title"] == "Vector Doc"
            assert results.results[0].score == 0.95
    finally:
        _allow_private_constructor.reset(token)  # pyright: ignore[reportPrivateUsage]


class ConcreteAzureAISearchTool(AzureAISearchTool):
    """Concrete implementation for testing."""

    async def _get_embedding(self, query: str) -> List[float]:
        return [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_create_keyword_search() -> None:
    """Test the create_keyword_search factory method."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="keyword_search",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=cast(TokenCredential, AzureKeyCredential("test-key")),
        search_fields=["title", "content"],
        select_fields=["title", "content"],
        filter="category eq 'test'",
        top=5,
    )

    assert tool.name == "keyword_search"
    assert tool.search_config.query_type == "keyword"
    assert tool.search_config.filter == "category eq 'test'"


@pytest.mark.asyncio
async def test_create_full_text_search() -> None:
    """Test the create_full_text_search factory method."""
    tool = ConcreteAzureAISearchTool.create_full_text_search(
        name="full_text_search",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=cast(TokenCredential, AzureKeyCredential("test-key")),
        search_fields=["title", "content"],
        select_fields=["title", "content"],
        filter="category eq 'test'",
        top=5,
    )

    assert tool.name == "full_text_search"
    assert tool.search_config.query_type == "fulltext"
    assert tool.search_config.search_fields == ["title", "content"]
    assert tool.search_config.select_fields == ["title", "content"]
    assert tool.search_config.filter == "category eq 'test'"
    assert tool.search_config.top == 5


@pytest.mark.asyncio
async def test_create_vector_search() -> None:
    """Test the create_vector_search factory method."""
    tool = ConcreteAzureAISearchTool.create_vector_search(
        name="vector_search",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
        vector_fields=["embedding"],
        select_fields=["title", "content"],
        top=5,
    )

    assert tool.name == "vector_search"
    assert tool.search_config.query_type == "vector"
    assert tool.search_config.vector_fields == ["embedding"]


@pytest.mark.asyncio
async def test_create_hybrid_search() -> None:
    """Test the create_hybrid_search factory method."""
    tool = ConcreteAzureAISearchTool.create_hybrid_search(
        name="hybrid_search",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
        vector_fields=["embedding"],
        search_fields=["title", "content"],
        select_fields=["title", "content"],
        top=5,
    )

    assert tool.name == "hybrid_search"
    assert tool.search_config.query_type == "hybrid"
    assert tool.search_config.vector_fields == ["embedding"]
    assert tool.search_config.search_fields == ["title", "content"]


@pytest.mark.asyncio
async def test_run_invalid_query() -> None:
    """Test the run method with an invalid query format."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    invalid_query: Dict[str, Any] = {"invalid_key": "invalid_value"}
    with pytest.raises(ValueError, match="Invalid search query format"):
        await tool.run(invalid_query)


@pytest.mark.asyncio
async def test_process_credential_dict() -> None:
    """Test the _process_credential method with a dictionary credential."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential={"api_key": "test-key"},
    )

    assert isinstance(tool.search_config.credential, AzureKeyCredential)
    assert tool.search_config.credential.key == "test-key"


@pytest.mark.asyncio
async def test_run_empty_query() -> None:
    """Test the run method with an empty query."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    with patch.object(tool, "_get_client", AsyncMock()):
        with pytest.raises(ValueError, match="Invalid search query format"):
            await tool.run("")


@pytest.mark.asyncio
async def test_get_client_initialization() -> None:
    """Test the _get_client method for proper initialization."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    assert tool.search_config.endpoint == "https://test.search.windows.net"
    assert tool.search_config.index_name == "test-index"

    with patch("azure.search.documents.aio.SearchClient", autospec=True) as mock_client:
        mock_client.return_value = AsyncMock()
        await tool.run("test query", CancellationToken())
        mock_client.assert_called_once()


@pytest.mark.asyncio
async def test_return_value_as_string() -> None:
    """Test the return_value_as_string method for formatting search results."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    results = SearchResults(
        results=[
            SearchResult(score=0.95, content={"title": "Doc 1"}, metadata={}),
            SearchResult(score=0.85, content={"title": "Doc 2"}, metadata={}),
        ]
    )

    result_string = tool.return_value_as_string(results)
    assert "Result 1 (Score: 0.95): title: Doc 1" in result_string
    assert "Result 2 (Score: 0.85): title: Doc 2" in result_string


@pytest.mark.asyncio
async def test_return_value_as_string_empty() -> None:
    """Test the return_value_as_string method with empty results."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    results = SearchResults(results=[])
    result_string = tool.return_value_as_string(results)
    assert result_string == "No results found."


@pytest.mark.asyncio
async def test_load_component() -> None:
    """Test the load_component method for proper deserialization."""
    model = {
        "provider": "autogen_ext.tools.azure.BaseAzureAISearchTool",
        "config": {
            "name": "test_tool",
            "endpoint": "https://test.search.windows.net",
            "index_name": "test-index",
            "credential": {"api_key": "test-key"},
            "query_type": "keyword",
            "search_fields": ["title", "content"],
            "select_fields": ["title", "content"],
            "top": 5,
        },
    }

    tool = ConcreteAzureAISearchTool.load_component(model)
    assert tool.name == "test_tool"
    assert tool.search_config.query_type == "keyword"
    assert tool.search_config.search_fields == ["title", "content"]
