"""Test fixtures for Azure AI Search tool tests."""

import warnings
from typing import Any, Dict, Iterator, List, Protocol, TypeVar, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import ComponentModel

T = TypeVar("T")

try:
    from azure.core.credentials import AzureKeyCredential, TokenCredential

    azure_sdk_available = True
except ImportError:
    azure_sdk_available = False

skip_if_no_azure_sdk = pytest.mark.skipif(
    not azure_sdk_available, reason="Azure SDK components (azure-search-documents, azure-identity) not available"
)


class AccessTokenProtocol(Protocol):
    """Protocol matching Azure AccessToken."""

    token: str
    expires_on: int


class MockAccessToken:
    """Mock implementation of AccessToken."""

    def __init__(self, token: str, expires_on: int) -> None:
        self.token = token
        self.expires_on = expires_on


class MockAzureKeyCredential:
    """Mock implementation of AzureKeyCredential."""

    def __init__(self, key: str) -> None:
        self.key = key


class MockTokenCredential:
    """Mock implementation of TokenCredential for testing."""

    def get_token(
        self,
        *scopes: str,
        claims: str | None = None,
        tenant_id: str | None = None,
        enable_cae: bool = False,
        **kwargs: Any,
    ) -> AccessTokenProtocol:
        """Mock get_token method that implements TokenCredential protocol."""
        return MockAccessToken("mock-token", 12345)


CredentialType = Union[
    AzureKeyCredential,  # pyright: ignore [reportPossiblyUnboundVariable]
    TokenCredential,  # pyright: ignore [reportPossiblyUnboundVariable]
    MockAzureKeyCredential,
    MockTokenCredential,
    Any,
]

needs_azure_sdk = pytest.mark.skipif(not azure_sdk_available, reason="Azure SDK not available")

warnings.filterwarnings(
    "ignore",
    message="Type google.*uses PyType_Spec with a metaclass that has custom tp_new",
    category=DeprecationWarning,
)


@pytest.fixture
def mock_vectorized_query() -> MagicMock:
    """Create a mock VectorizedQuery for testing."""
    if azure_sdk_available:
        from azure.search.documents.models import VectorizedQuery

        return MagicMock(spec=VectorizedQuery)
    else:
        return MagicMock()


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
            "credential": AzureKeyCredential("test-key") if azure_sdk_available else {"api_key": "test-key"},  # pyright: ignore [reportPossiblyUnboundVariable]
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
            "credential": AzureKeyCredential("test-key") if azure_sdk_available else {"api_key": "test-key"},  # pyright: ignore [reportPossiblyUnboundVariable]
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
            "credential": AzureKeyCredential("test-key") if azure_sdk_available else {"api_key": "test-key"},  # pyright: ignore [reportPossiblyUnboundVariable]
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
            "credential": AzureKeyCredential("test-key") if azure_sdk_available else {"api_key": "test-key"},  # pyright: ignore [reportPossiblyUnboundVariable]
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
def mock_search_client(mock_search_response: List[Dict[str, Any]]) -> Iterator[MagicMock]:
    """Create a mock search client for testing, with the patch active."""
    mock_client_instance = MagicMock()
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    search_results_iterator = AsyncIterator(mock_search_response)
    mock_client_instance.search = MagicMock(return_value=search_results_iterator)

    patch_target = "autogen_ext.tools.azure._ai_search.SearchClient"
    patcher = patch(patch_target, return_value=mock_client_instance)

    patcher.start()
    yield mock_client_instance
    patcher.stop()
