"""Tests for the Azure AI Search tool."""

from typing import Any, AsyncGenerator, Dict, List, cast
from unittest.mock import AsyncMock, patch

import pytest
from autogen_core import CancellationToken
from autogen_ext.tools.azure._ai_search import (
    AzureAISearchTool,
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
async def test_create_hybrid_search() -> None:
    """Test the create_hybrid_search factory method."""
    tool = ConcreteAzureAISearchTool.create_hybrid_search(
        name="hybrid_search",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=cast(TokenCredential, AzureKeyCredential("test-key")),
        vector_fields=["embedding"],
        search_fields=["title", "content"],
        select_fields=["title", "content"],
        filter="category eq 'test'",
        top=5,
    )

    assert tool.name == "hybrid_search"
    assert tool.search_config.query_type == "hybrid"
    assert tool.search_config.vector_fields == ["embedding"]
    assert tool.search_config.search_fields == ["title", "content"]
    assert tool.search_config.filter == "category eq 'test'"
    assert tool.search_config.top == 5


@pytest.mark.asyncio
async def test_process_credential() -> None:
    """Test the _process_credential method."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential={"api_key": "test-key"},
    )

    assert isinstance(tool.search_config.credential, AzureKeyCredential)
    assert tool.search_config.credential.key == "test-key"

    with pytest.raises(ValueError, match="credential cannot be None"):
        ConcreteAzureAISearchTool.create_keyword_search(
            name="test_tool",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential={},
        )
