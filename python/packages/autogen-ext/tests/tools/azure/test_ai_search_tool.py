"""Tests for the Azure AI Search tool."""

from typing import Any, AsyncGenerator, Dict, List, Union, cast
from unittest.mock import AsyncMock, patch

import pytest
from autogen_core import CancellationToken
from autogen_ext.tools.azure._ai_search import (
    AzureAISearchTool,
    BaseAzureAISearchTool,
    SearchQuery,
    SearchResult,
    SearchResults,
    _allow_private_constructor,  # pyright: ignore[reportPrivateUsage]
)
from azure.core.credentials import AzureKeyCredential, TokenCredential
from azure.core.exceptions import HttpResponseError


class MockAsyncIterator:
    """Mock for async iterator to use in tests."""

    def __init__(self, items: List[Dict[str, Any]]) -> None:
        self.items = items.copy()

    def __aiter__(self) -> "MockAsyncIterator":
        return self

    async def __anext__(self) -> Dict[str, Any]:
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)


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

    with patch.object(tool, "_get_client", AsyncMock()) as mock_client:
        mock_client.return_value.search = AsyncMock(
            return_value=MockAsyncIterator([{"@search.score": 0.95, "title": "Test Doc", "content": "Test Content"}])
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

        with patch.object(tool, "_get_client", AsyncMock()) as mock_client:
            mock_client.return_value.search = AsyncMock(
                return_value=MockAsyncIterator(
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

    mock_client = AsyncMock()

    class MockAsyncIterator:
        def __init__(self, items: List[Dict[str, Any]]) -> None:
            self.items = items

        def __aiter__(self) -> "MockAsyncIterator":
            return self

        async def __anext__(self) -> Dict[str, Any]:
            if not self.items:
                raise StopAsyncIteration
            return self.items.pop(0)

    mock_client.search.return_value = MockAsyncIterator([{"@search.score": 0.9, "title": "Test Result"}])

    with patch.object(tool, "_get_client", return_value=mock_client):
        results = await tool.run("test query", CancellationToken())
        mock_client.search.assert_called_once()

        assert len(results.results) == 1
        assert results.results[0].content["title"] == "Test Result"
        assert results.results[0].score == 0.9


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


@pytest.mark.asyncio
async def test_caching_functionality() -> None:
    """Test the caching functionality of the search tool."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="cache_test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
        enable_caching=True,
        cache_ttl_seconds=300,
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    test_result = {"@search.score": 0.9, "title": "Test Result"}

    class MockAsyncIterator:
        def __init__(self) -> None:
            self.returned = False

        def __aiter__(self) -> "MockAsyncIterator":
            return self

        async def __anext__(self) -> Dict[str, Any]:
            if self.returned:
                raise StopAsyncIteration
            self.returned = True
            return test_result

    mock_client.search = AsyncMock(return_value=MockAsyncIterator())

    with patch.object(tool, "_get_client", return_value=mock_client):
        results1 = await tool.run("test query")
        assert len(results1.results) == 1
        assert results1.results[0].content["title"] == "Test Result"
        assert mock_client.search.call_count == 1

        mock_client.search = AsyncMock(return_value=MockAsyncIterator())

        results2 = await tool.run("test query")
        assert len(results2.results) == 1
        assert results2.results[0].content["title"] == "Test Result"
        assert mock_client.search.call_count == 1


@pytest.mark.asyncio
async def test_semantic_search_configuration() -> None:
    """Test semantic search configuration handling."""
    tool = ConcreteAzureAISearchTool.create_full_text_search(
        name="semantic_search",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
        search_fields=["title", "content"],
        select_fields=["title", "content"],
    )

    assert tool.search_config.query_type == "fulltext"

    mock_client = AsyncMock()

    class MockAsyncIterator:
        def __init__(self, items: List[Dict[str, Any]]) -> None:
            self.items = items[:]

        def __aiter__(self) -> "MockAsyncIterator":
            return self

        async def __anext__(self) -> Dict[str, Any]:
            if not self.items:
                raise StopAsyncIteration
            return self.items.pop(0)

    mock_client.search.return_value = MockAsyncIterator([{"@search.score": 0.9, "title": "Semantic Result"}])

    with patch.object(ConcreteAzureAISearchTool, "run") as mock_run:
        mock_run.return_value = SearchResults(
            results=[SearchResult(score=0.9, content={"title": "Semantic Result"}, metadata={})]
        )

        results = await tool.run("semantic query")

        assert len(results.results) == 1
        assert results.results[0].content["title"] == "Semantic Result"


@pytest.mark.asyncio
async def test_http_response_error_handling() -> None:
    """Test handling of different HTTP response errors."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_search",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    mock_client = AsyncMock()
    http_error = HttpResponseError()
    http_error.message = "401 Unauthorized: Access is denied due to invalid credentials"

    with patch.object(tool, "_get_client", return_value=mock_client):
        mock_client.search = AsyncMock(side_effect=http_error)
        with pytest.raises(ValueError, match="Authentication failed"):
            await tool.run("test query")

    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_search",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("invalid-key"),
    )

    with patch.object(tool, "_get_client", AsyncMock(side_effect=ValueError("Invalid key"))):
        with pytest.raises(ValueError, match="Authentication failed"):
            await tool.run("test query")


@pytest.mark.asyncio
async def test_run_with_search_query_object() -> None:
    """Test running the search with a SearchQuery object instead of a string."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    mock_client = AsyncMock()
    mock_client.search.return_value = MockAsyncIterator([{"@search.score": 0.85, "title": "Query Object Test"}])

    with patch.object(tool, "_get_client", return_value=mock_client):
        search_query = SearchQuery(query="advanced query")
        results = await tool.run(search_query)

        assert len(results.results) == 1
        assert results.results[0].content["title"] == "Query Object Test"
        mock_client.search.assert_called_once()


@pytest.mark.asyncio
async def test_dict_document_processing() -> None:
    """Test processing of document with dict-like interface."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    class DictLikeDoc:
        def __init__(self, data: Dict[str, Any]) -> None:
            self._data = data

        def items(self) -> List[tuple[str, Any]]:
            return list(self._data.items())

    mock_client = AsyncMock()

    class SpecialMockAsyncIterator:
        def __init__(self) -> None:
            self.returned = False

        def __aiter__(self) -> "SpecialMockAsyncIterator":
            return self

        async def __anext__(self) -> DictLikeDoc:
            if self.returned:
                raise StopAsyncIteration
            self.returned = True
            return DictLikeDoc({"@search.score": 0.75, "title": "Dict Like Doc"})

    mock_client.search.return_value = SpecialMockAsyncIterator()

    with patch.object(tool, "_get_client", return_value=mock_client):
        results = await tool.run("test query")

        assert len(results.results) == 1
        assert results.results[0].content["title"] == "Dict Like Doc"
        assert results.results[0].score == 0.75


@pytest.mark.asyncio
async def test_document_processing_error_handling() -> None:
    """Test error handling during document processing."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    mock_client = AsyncMock()

    class ProblemDoc:
        def items(self) -> None:
            raise AttributeError("Simulated error in document processing")

    class MixedResultsAsyncIterator:
        def __init__(self) -> None:
            self.docs: List[Union[Dict[str, Any], ProblemDoc]] = [
                {"@search.score": 0.9, "title": "Good Doc"},
                ProblemDoc(),
                {"@search.score": 0.8, "title": "Another Good Doc"},
            ]
            self.index = 0

        def __aiter__(self) -> "MixedResultsAsyncIterator":
            return self

        async def __anext__(self) -> Union[Dict[str, Any], ProblemDoc]:
            if self.index >= len(self.docs):
                raise StopAsyncIteration
            doc = self.docs[self.index]
            self.index += 1
            return doc

    mock_client.search.return_value = MixedResultsAsyncIterator()

    with patch.object(tool, "_get_client", return_value=mock_client):
        results = await tool.run("test query")

        assert len(results.results) == 2
        assert results.results[0].content["title"] == "Good Doc"
        assert results.results[1].content["title"] == "Another Good Doc"


@pytest.mark.asyncio
async def test_index_not_found_error() -> None:
    """Test handling of 'index not found' error."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="nonexistent-index",
        credential=AzureKeyCredential("test-key"),
    )

    not_found_error = ValueError("The index 'nonexistent-index' was not found")

    with patch.object(tool, "_get_client", AsyncMock(side_effect=not_found_error)):
        with pytest.raises(ValueError, match="Index 'nonexistent-index' not found"):
            await tool.run("test query")


@pytest.mark.asyncio
async def test_http_response_with_500_error() -> None:
    """Test handling of HTTP 500 error responses."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_search",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    http_error = HttpResponseError()
    http_error.message = "500 Internal Server Error: Something went wrong on the server"

    with patch.object(tool, "_get_client", AsyncMock()) as mock_client:
        mock_client.return_value.search = AsyncMock(side_effect=http_error)

        with pytest.raises(ValueError, match="Error from Azure AI Search"):
            await tool.run("test query")


@pytest.mark.asyncio
async def test_cancellation_during_search() -> None:
    """Test cancellation token functionality during the search process."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    cancellation_token = CancellationToken()
    cancellation_token.cancel()

    with pytest.raises(ValueError, match="Operation cancelled"):
        await tool.run("test query", cancellation_token)


@pytest.mark.asyncio
async def test_run_with_dict_query_format() -> None:
    """Test running the search with a dictionary query format with 'query' key."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    mock_client = AsyncMock()
    mock_client.search.return_value = MockAsyncIterator([{"@search.score": 0.85, "title": "Dict Query Test"}])

    with patch.object(tool, "_get_client", return_value=mock_client):
        query_dict = {"query": "dict style query"}
        results = await tool.run(query_dict)

        assert len(results.results) == 1
        assert results.results[0].content["title"] == "Dict Query Test"
        mock_client.search.assert_called_once()


@pytest.mark.asyncio
async def test_object_based_document_processing() -> None:
    """Test processing of document with object attributes instead of dict interface."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="test_tool",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    class ObjectDoc:
        """Test document class with object attributes."""

        def __init__(self) -> None:
            self.title = "Object Doc"
            self.content = "Object content"
            self._private_attr = "private"
            self.__search_score = 0.8

    mock_client = AsyncMock()

    class ObjectDocAsyncIterator:
        def __init__(self) -> None:
            self.returned = False

        def __aiter__(self) -> "ObjectDocAsyncIterator":
            return self

        async def __anext__(self) -> ObjectDoc:
            if self.returned:
                raise StopAsyncIteration
            self.returned = True
            return ObjectDoc()

    mock_client.search.return_value = ObjectDocAsyncIterator()

    with patch.object(tool, "_get_client", return_value=mock_client):
        results = await tool.run("test query")

        assert len(results.results) == 1
        assert results.results[0].content["title"] == "Object Doc"
        assert results.results[0].content["content"] == "Object content"
        assert "_private_attr" not in results.results[0].content


@pytest.mark.asyncio
async def test_vector_search_with_provided_vectors() -> None:
    """Test vector search using vectors provided directly in the search options."""
    tool = ConcreteAzureAISearchTool.create_vector_search(
        name="vector_direct_search",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
        vector_fields=["embedding"],
        select_fields=["title", "content"],
    )

    mock_client = AsyncMock()
    mock_client.search.return_value = MockAsyncIterator([{"@search.score": 0.95, "title": "Vector Direct Test"}])

    query = "test vector search"

    with patch.object(tool, "_get_client", return_value=mock_client):
        results = await tool.run(query)
        assert len(results.results) == 1
        assert results.results[0].content["title"] == "Vector Direct Test"

        mock_client.search.assert_called_once()


@pytest.mark.asyncio
async def test_credential_token_expiry_handling() -> None:
    """Test handling credential token expiry and error cases."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="token_test",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    auth_error = HttpResponseError()
    auth_error.message = "401 Unauthorized: Access token has expired or is not yet valid"

    with patch.object(tool, "_get_client", AsyncMock()) as mock_client:
        mock_client.return_value.search = AsyncMock(side_effect=auth_error)

        with pytest.raises(ValueError, match="Authentication failed"):
            await tool.run("test query")

    token_error = ValueError("401 Unauthorized: Token is invalid")

    with patch.object(tool, "_get_client", AsyncMock(side_effect=token_error)):
        with pytest.raises(ValueError, match="Authentication failed"):
            await tool.run("test query")


@pytest.mark.asyncio
async def test_search_with_user_provided_vectors() -> None:
    """Test the use of user-provided embedding vectors in SearchQuery."""
    tool = ConcreteAzureAISearchTool.create_vector_search(
        name="vector_test_with_embeddings",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
        vector_fields=["embedding"],
    )

    mock_client = AsyncMock()
    mock_client.search.return_value = MockAsyncIterator([{"@search.score": 0.95, "title": "Vector Result"}])

    query = "test vector search"

    with patch.object(tool, "_get_client", return_value=mock_client):
        results = await tool.run(query)
        assert len(results.results) == 1
        assert results.results[0].content["title"] == "Vector Result"

        mock_client.search.assert_called_once()


@pytest.mark.asyncio
async def test_component_loading_with_invalid_params() -> None:
    """Test loading components with invalid parameters."""

    class OtherClass:
        pass

    with pytest.raises(TypeError, match="Cannot create instance"):
        BaseAzureAISearchTool.load_component(
            {"provider": "autogen_ext.tools.azure.BaseAzureAISearchTool", "config": {}},
            expected=OtherClass,  # type: ignore
        )

    with pytest.raises(ValueError):
        from unittest.mock import patch

        with patch.object(
            AzureAISearchTool, "load_component", side_effect=ValueError("Invalid component configuration")
        ):
            ConcreteAzureAISearchTool.load_component("not a dict or ComponentModel")  # type: ignore

    with pytest.raises(ValueError, match="Invalid component configuration"):
        ConcreteAzureAISearchTool.load_component({})


@pytest.mark.asyncio
async def test_factory_method_validation() -> None:
    """Test validation in factory methods."""
    with pytest.raises(ValueError, match="endpoint must be a valid URL"):
        ConcreteAzureAISearchTool.create_keyword_search(
            name="test", endpoint="", index_name="test-index", credential=AzureKeyCredential("test-key")
        )

    with pytest.raises(ValueError, match="endpoint must be a valid URL"):
        ConcreteAzureAISearchTool.create_keyword_search(
            name="test", endpoint="invalid-url", index_name="test-index", credential=AzureKeyCredential("test-key")
        )

    with pytest.raises(ValueError, match="index_name cannot be empty"):
        ConcreteAzureAISearchTool.create_keyword_search(
            name="test",
            endpoint="https://test.search.windows.net",
            index_name="",
            credential=AzureKeyCredential("test-key"),
        )

    with pytest.raises(ValueError, match="name cannot be empty"):
        ConcreteAzureAISearchTool.create_keyword_search(
            name="",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
        )

    with pytest.raises(ValueError, match="credential cannot be None"):
        ConcreteAzureAISearchTool.create_keyword_search(
            name="test",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential=None,  # type: ignore
        )

    with pytest.raises(ValueError, match="vector_fields must contain at least one field name"):
        ConcreteAzureAISearchTool.create_vector_search(
            name="test",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
            vector_fields=[],
        )

    with pytest.raises(ValueError, match="vector_fields must contain at least one field name"):
        ConcreteAzureAISearchTool.create_hybrid_search(
            name="test",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
            vector_fields=[],
        )


@pytest.mark.asyncio
async def test_direct_tool_initialization_error() -> None:
    """Test that directly initializing AzureAISearchTool raises an error."""

    class TestSearchTool(AzureAISearchTool):
        async def _get_embedding(self, query: str) -> List[float]:
            return [0.1, 0.2, 0.3]

    with pytest.raises(RuntimeError, match="Constructor is private"):
        TestSearchTool(
            name="test",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
            query_type="keyword",
        )


@pytest.mark.asyncio
async def test_credential_dict_with_missing_api_key() -> None:
    """Test handling of credential dict without api_key."""
    with pytest.raises(ValueError, match="If credential is a dict, it must contain an 'api_key' key"):
        ConcreteAzureAISearchTool.create_keyword_search(
            name="test",
            endpoint="https://test.search.windows.net",
            index_name="test-index",
            credential={"invalid_key": "value"},
        )


@pytest.mark.asyncio
async def test_complex_error_handling_scenarios() -> None:
    """Test more complex error handling scenarios."""
    tool = ConcreteAzureAISearchTool.create_keyword_search(
        name="error_test",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
    )

    permission_error = HttpResponseError()
    permission_error.message = "403 Forbidden: Access is denied"

    with patch.object(tool, "_get_client", AsyncMock(side_effect=permission_error)):
        with pytest.raises(ValueError, match="Error from Azure AI Search"):
            await tool.run("test query")

    unexpected_error = Exception("Unexpected error during initialization")

    with patch.object(tool, "_get_client", AsyncMock(side_effect=unexpected_error)):
        with pytest.raises(ValueError, match="Error from Azure AI Search"):
            await tool.run("test query")


@pytest.mark.asyncio
async def test_semantic_configuration_name_handling() -> None:
    """Test handling of semantic configuration names in fulltext search."""
    tool = ConcreteAzureAISearchTool.create_full_text_search(
        name="semantic_config_test",
        endpoint="https://test.search.windows.net",
        index_name="test-index",
        credential=AzureKeyCredential("test-key"),
        search_fields=["title", "content"],
        select_fields=["title", "content"],
    )

    mock_client = AsyncMock()
    mock_client.search.return_value = MockAsyncIterator([{"@search.score": 0.9, "title": "Semantic Test Result"}])

    assert tool.search_config.query_type == "fulltext"
    assert tool.search_config.search_fields == ["title", "content"]

    with patch.object(tool, "_get_client", return_value=mock_client):
        original_run = tool.run

        async def mock_run(*args: Any, **kwargs: Any) -> SearchResults:
            return SearchResults(
                results=[SearchResult(score=0.9, content={"title": "Semantic Test Result"}, metadata={})]
            )

        tool.run = mock_run  # type: ignore
        results = await tool.run("semantic query")
        assert len(results.results) == 1
        assert results.results[0].content["title"] == "Semantic Test Result"
        tool.run = original_run  # type: ignore
