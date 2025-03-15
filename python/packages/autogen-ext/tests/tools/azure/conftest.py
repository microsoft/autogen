"""Test fixtures for Azure AI Search tool tests."""

import sys
import warnings
from typing import Any, Dict, Generator, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import ComponentModel

warnings.filterwarnings(
    "ignore",
    message="Type google.*uses PyType_Spec with a metaclass that has custom tp_new",
    category=DeprecationWarning,
)


class MockAzureKeyCredential:
    """Mock implementation of AzureKeyCredential."""

    def __init__(self, key: str = "test-key") -> None:
        self.key = key


class MockTokenCredential:
    """Mock implementation of TokenCredential."""

    def get_token(self, *scopes: str, **kwargs: Any) -> MagicMock:
        return MagicMock(token="mock-token")


class MockResourceNotFoundError(Exception):
    """Mock implementation of ResourceNotFoundError."""

    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        self.message = message
        super().__init__(message)


class MockHttpResponseError(Exception):
    """Mock implementation of HttpResponseError."""

    def __init__(self, message: str = "Http error", **kwargs: Any) -> None:
        self.message = message
        super().__init__(message)


for module_name in [
    "azure.core",
    "azure.core.credentials",
    "azure.core.exceptions",
    "azure.identity",
    "azure.cosmos",
    "azure.cosmos.cosmos_client",
    "azure.cosmos.partition_key",
    "azure.cosmos.container",
    "azure.cosmos.database",
    "azure.cosmos.exceptions",
    "azure.search.documents",
    "azure.search.documents.aio",
    "azure.search.documents.models",
    "azure.search.documents.indexes",
    "azure.search.documents.indexes.models",
    "azure.search.documents.indexes.aio",
    "azure.mgmt.search",
    "azure.storage.blob",
    "azure.storage.queue",
    "azure.storage.common",
    "azure.ai.ml",
    "azure.ai.formrecognizer",
    "azure.openai",
]:
    if module_name not in sys.modules:
        sys.modules[module_name] = MagicMock()


credentials = sys.modules["azure.core.credentials"]
credentials.AzureKeyCredential = MockAzureKeyCredential  # type: ignore
credentials.TokenCredential = MockTokenCredential  # type: ignore

exceptions = sys.modules["azure.core.exceptions"]
exceptions.ResourceNotFoundError = MockResourceNotFoundError  # type: ignore
exceptions.HttpResponseError = MockHttpResponseError  # type: ignore

cosmos_module = sys.modules["azure.cosmos"]
cosmos_module.CosmosClient = MagicMock  # type: ignore
cosmos_module.ContainerProxy = MagicMock  # type: ignore
cosmos_module.DatabaseProxy = MagicMock  # type: ignore

partition_key_module = sys.modules["azure.cosmos.partition_key"]
partition_key_module.PartitionKey = MagicMock  # type: ignore

blob_module = sys.modules["azure.storage.blob"]
blob_module.BlobServiceClient = MagicMock  # type: ignore
blob_module.ContainerClient = MagicMock  # type: ignore
blob_module.BlobClient = MagicMock  # type: ignore

if "azure.identity" in sys.modules:
    identity_module = sys.modules["azure.identity"]
    identity_module.DefaultAzureCredential = MagicMock  # type: ignore
    identity_module.ClientSecretCredential = MagicMock  # type: ignore


@pytest.fixture
def mock_vectorized_query() -> Generator[MagicMock, None, None]:
    """Create a mock VectorizedQuery for testing."""
    with patch("azure.search.documents.models.VectorizedQuery") as mock:
        yield mock


@pytest.fixture
def test_config() -> ComponentModel:
    """Create a test configuration for the Azure AI Search tool."""
    return ComponentModel(
        provider="autogen_ext.tools.azure.test_ai_search_tool.MockAzureAISearchTool",
        config={
            "name": "TestAzureSearch",
            "description": "Test Azure AI Search Tool",
            "endpoint": "https://test-search-service.search.windows.net",
            "index_name": "test-index",
            "api_version": "2023-10-01-Preview",
            "credential": {"api_key": "test-key"},
            "query_type": "simple",
            "search_fields": ["content", "title"],
            "select_fields": ["id", "content", "title", "source"],
            "top": 5,
        },
    )


@pytest.fixture
def semantic_config() -> ComponentModel:
    """Create a test configuration for semantic search."""
    return ComponentModel(
        provider="autogen_ext.tools.azure.test_ai_search_tool.MockAzureAISearchTool",
        config={
            "name": "TestAzureSearch",
            "description": "Test Azure AI Search Tool",
            "endpoint": "https://test-search-service.search.windows.net",
            "index_name": "test-index",
            "api_version": "2023-10-01-Preview",
            "credential": {"api_key": "test-key"},
            "query_type": "semantic",
            "semantic_config_name": "test-semantic-config",
            "search_fields": ["content", "title"],
            "select_fields": ["id", "content", "title", "source"],
            "top": 5,
            "openai_client": MagicMock(),
            "embedding_model": "mock-embedding-model",
        },
    )


@pytest.fixture
def vector_config() -> ComponentModel:
    """Create a test configuration for vector search."""
    return ComponentModel(
        provider="autogen_ext.tools.azure.test_ai_search_tool.MockAzureAISearchTool",
        config={
            "name": "TestAzureSearch",
            "description": "Test Azure AI Search Tool",
            "endpoint": "https://test-search-service.search.windows.net",
            "index_name": "test-index",
            "api_version": "2023-10-01-Preview",
            "credential": {"api_key": "test-key"},
            "query_type": "vector",
            "vector_fields": ["embedding"],
            "select_fields": ["id", "content", "title", "source"],
            "top": 5,
            "openai_client": MagicMock(),
            "embedding_model": "mock-embedding-model",
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
