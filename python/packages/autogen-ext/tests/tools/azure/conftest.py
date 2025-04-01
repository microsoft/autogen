"""Test fixtures for Azure AI Search tool tests."""

import warnings
from typing import Any, Dict, Generator, List, Protocol, Type, TypeVar, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import ComponentModel

T = TypeVar("T")


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


try:
    from azure.core.credentials import AccessToken, AzureKeyCredential, TokenCredential

    _access_token_type: Type[AccessToken] = AccessToken
    azure_sdk_available = True
except ImportError:
    AzureKeyCredential = MockAzureKeyCredential  # type: ignore
    TokenCredential = MockTokenCredential  # type: ignore
    _access_token_type = MockAccessToken  # type: ignore
    azure_sdk_available = False

CredentialType = Union[AzureKeyCredential, TokenCredential, MockAzureKeyCredential, MockTokenCredential, Any]

needs_azure_sdk = pytest.mark.skipif(not azure_sdk_available, reason="Azure SDK not available")

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


def test_validate_credentials_scenarios() -> None:
    """Test all validate_credentials scenarios to ensure full code coverage."""
    import sys

    from autogen_ext.tools.azure._config import AzureAISearchConfig

    module_path = sys.modules[AzureAISearchConfig.__module__].__file__
    if module_path is not None:
        assert "autogen-ext" in module_path

    data: Any = "not a dict"
    result: Any = AzureAISearchConfig.validate_credentials(data)  # type: ignore
    assert result == data

    data_empty: Dict[str, Any] = {}
    result_empty: Dict[str, Any] = AzureAISearchConfig.validate_credentials(data_empty)  # type: ignore
    assert isinstance(result_empty, dict)

    data_items: Dict[str, Any] = {"key1": "value1", "key2": "value2"}
    result_items: Dict[str, Any] = AzureAISearchConfig.validate_credentials(data_items)  # type: ignore
    assert result_items["key1"] == "value1"
    assert result_items["key2"] == "value2"

    data_with_api_key: Dict[str, Any] = {
        "name": "test",
        "endpoint": "https://test.search.windows.net",
        "index_name": "test-index",
        "credential": {"api_key": "test-key"},
    }
    result_with_api_key: Dict[str, Any] = AzureAISearchConfig.validate_credentials(data_with_api_key)  # type: ignore

    cred = result_with_api_key["credential"]  # type: ignore
    assert isinstance(cred, (AzureKeyCredential, MockAzureKeyCredential))
    assert hasattr(cred, "key")
    assert cred.key == "test-key"  # type: ignore

    credential: Any = AzureKeyCredential("test-key")
    data_with_credential: Dict[str, Any] = {
        "name": "test",
        "endpoint": "https://test.search.windows.net",
        "index_name": "test-index",
        "credential": credential,
    }
    result_with_credential: Dict[str, Any] = AzureAISearchConfig.validate_credentials(data_with_credential)  # type: ignore
    assert result_with_credential["credential"] is credential

    data_without_api_key: Dict[str, Any] = {
        "name": "test",
        "endpoint": "https://test.search.windows.net",
        "index_name": "test-index",
        "credential": {"username": "test-user", "password": "test-pass"},
    }
    result_without_api_key: Dict[str, Any] = AzureAISearchConfig.validate_credentials(data_without_api_key)  # type: ignore
    assert result_without_api_key["credential"] == {"username": "test-user", "password": "test-pass"}


def test_model_dump_scenarios() -> None:
    """Test all model_dump scenarios to ensure full code coverage."""
    import sys

    from autogen_ext.tools.azure._config import AzureAISearchConfig

    module_path = sys.modules[AzureAISearchConfig.__module__].__file__
    if module_path is not None:
        assert "autogen-ext" in module_path

    config = AzureAISearchConfig(
        name="test",
        endpoint="https://endpoint",
        index_name="index",
        credential=AzureKeyCredential("key"),  # type: ignore
    )
    result = config.model_dump()
    assert result["credential"] == {"type": "AzureKeyCredential"}

    if azure_sdk_available:
        from azure.core.credentials import AccessToken
        from azure.core.credentials import TokenCredential as RealTokenCredential

        class TestTokenCredential(RealTokenCredential):
            def get_token(self, *args: Any, **kwargs: Any) -> AccessToken:
                """Override of get_token method that returns proper type."""
                return AccessToken("test-token", 12345)

        config = AzureAISearchConfig(
            name="test", endpoint="https://endpoint", index_name="index", credential=TestTokenCredential()
        )
        result = config.model_dump()
        assert result["credential"] == {"type": "TokenCredential"}
    else:
        pytest.skip("Skipping TokenCredential test - Azure SDK not available")
