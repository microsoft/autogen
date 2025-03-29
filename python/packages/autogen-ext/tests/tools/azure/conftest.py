"""Test fixtures for Azure AI Search tool tests."""

import warnings
from typing import Any, Dict, Generator, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import ComponentModel


class MockAzureKeyCredential:
    """Mock implementation of AzureKeyCredential."""

    def __init__(self, key: str) -> None:
        self.key = key


try:
    from azure.core.credentials import AzureKeyCredential

    azure_sdk_available = True
except ImportError:
    AzureKeyCredential = MockAzureKeyCredential  # type: ignore
    azure_sdk_available = False

warnings.filterwarnings(
    "ignore",
    message="Type google.*uses PyType_Spec with a metaclass that has custom tp_new",
    category=DeprecationWarning,
)


@pytest.fixture
def mock_vectorized_query() -> Generator[MagicMock, None, None]:
    """Create a mock VectorizedQuery for testing."""
    with patch("azure.search.documents.models.VectorizedQuery") as mock:
        yield mock


@pytest.fixture
def test_config() -> ComponentModel:
    """Return a test configuration for the Azure AI Search tool."""
    return ComponentModel(
        provider="autogen_ext.tools.azure.MockAzureAISearchTool",
        config={
            "name": "TestAzureSearch",
            "description": "Test Azure AI Search Tool",
            "endpoint": "https://test-search-service.search.windows.net",
            "index_name": "test-index",
            "api_version": "2023-10-01-Preview",
            "credential": AzureKeyCredential("test-key") if azure_sdk_available else {"api_key": "test-key"},
            "query_type": "keyword",
            "search_fields": ["content", "title"],
            "select_fields": ["id", "content", "title", "source"],
            "top": 5,
        },
    )


@pytest.fixture
def keyword_config() -> ComponentModel:
    """Return a keyword search configuration."""
    return ComponentModel(
        provider="autogen_ext.tools.azure.MockAzureAISearchTool",
        config={
            "name": "KeywordSearch",
            "description": "Keyword search tool",
            "endpoint": "https://test-search-service.search.windows.net",
            "index_name": "test-index",
            "credential": AzureKeyCredential("test-key") if azure_sdk_available else {"api_key": "test-key"},
            "query_type": "keyword",
            "search_fields": ["content", "title"],
            "select_fields": ["id", "content", "title", "source"],
        },
    )


@pytest.fixture
def vector_config() -> ComponentModel:
    """Create a test configuration for vector search."""
    return ComponentModel(
        provider="autogen_ext.tools.azure.MockAzureAISearchTool",
        config={
            "name": "VectorSearch",
            "description": "Vector search tool",
            "endpoint": "https://test-search-service.search.windows.net",
            "index_name": "test-index",
            "api_version": "2023-10-01-Preview",
            "credential": AzureKeyCredential("test-key") if azure_sdk_available else {"api_key": "test-key"},
            "query_type": "vector",
            "vector_fields": ["embedding"],
            "select_fields": ["id", "content", "title", "source"],
            "top": 5,
        },
    )


@pytest.fixture
def hybrid_config() -> ComponentModel:
    """Create a test configuration for hybrid search."""
    return ComponentModel(
        provider="autogen_ext.tools.azure.MockAzureAISearchTool",
        config={
            "name": "HybridSearch",
            "description": "Hybrid search tool",
            "endpoint": "https://test-search-service.search.windows.net",
            "index_name": "test-index",
            "api_version": "2023-10-01-Preview",
            "credential": AzureKeyCredential("test-key") if azure_sdk_available else {"api_key": "test-key"},
            "query_type": "keyword",
            "search_fields": ["content", "title"],
            "vector_fields": ["embedding"],
            "select_fields": ["id", "content", "title", "source"],
            "top": 5,
        },
    )


@pytest.fixture
def mock_search_response() -> List[Dict[str, Any]]:
    """Create a mock search response."""
    return [
        {
            "@search.score": 0.95,
            "id": "doc1",
            "content": "This is the first document content",
            "title": "Document 1",
            "source": "test-source-1",
        },
        {
            "@search.score": 0.85,
            "id": "doc2",
            "content": "This is the second document content",
            "title": "Document 2",
            "source": "test-source-2",
        },
    ]


class AsyncIterator:
    """Async iterator for testing."""

    def __init__(self, items: List[Dict[str, Any]]) -> None:
        self.items = items.copy()

    def __aiter__(self) -> "AsyncIterator":
        return self

    async def __anext__(self) -> Dict[str, Any]:
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)

    async def get_count(self) -> int:
        """Return count of items."""
        return len(self.items)


@pytest.fixture
def mock_search_client(mock_search_response: List[Dict[str, Any]]) -> tuple[MagicMock, Any]:
    """Create a mock search client for testing."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    search_results = AsyncIterator(mock_search_response)
    mock_client.search = MagicMock(return_value=search_results)

    patcher = patch("azure.search.documents.aio.SearchClient", return_value=mock_client)

    return mock_client, patcher
