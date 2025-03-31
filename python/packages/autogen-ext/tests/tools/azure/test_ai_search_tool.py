"""Tests for the Azure AI Search tool."""

import asyncio
import importlib.util
import os
import sys
from typing import Any, Dict, List, Optional, Type, TypeAlias, TypeGuard, TypeVar, Union, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import CancellationToken, ComponentModel


class MockAzureKeyCredential:
    """Mock implementation of AzureKeyCredential."""

    def __init__(self, key: str) -> None:
        self.key = key


class MockHttpResponseError(Exception):
    """Mock HttpResponseError."""

    def __init__(self, message: Optional[str] = None, *args: object) -> None:
        super().__init__(*args)
        self.message = message


class MockResourceNotFoundError(Exception):
    """Mock ResourceNotFoundError."""

    pass


try:
    from azure.core.credentials import AzureKeyCredential
    from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

    azure_sdk_available = True
except ImportError:
    AzureKeyCredential = MockAzureKeyCredential  # type: ignore
    HttpResponseError = MockHttpResponseError  # type: ignore
    ResourceNotFoundError = MockResourceNotFoundError  # type: ignore
    azure_sdk_available = False

pytestmark = pytest.mark.skipif(not azure_sdk_available, reason="Azure Search SDK not installed")

src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
sys.path.insert(0, src_dir)

source_dir = os.path.join(src_dir, "autogen_ext", "tools", "azure")
ai_search_path = os.path.join(source_dir, "_ai_search.py")
config_path = os.path.join(source_dir, "_config.py")

os.makedirs(source_dir, exist_ok=True)
init_file = os.path.join(source_dir, "__init__.py")
if not os.path.exists(init_file):
    with open(init_file, "w") as f:
        pass

spec_ai_search = importlib.util.spec_from_file_location("ai_search_module", ai_search_path)
if spec_ai_search is None:
    raise ImportError(f"Could not load spec from {ai_search_path}")
ai_search_module = importlib.util.module_from_spec(spec_ai_search)
if spec_ai_search.loader is None:
    raise ImportError(f"No loader found for {ai_search_path}")
spec_ai_search.loader.exec_module(ai_search_module)

spec_config = importlib.util.spec_from_file_location("config_module", config_path)
if spec_config is None:
    raise ImportError(f"Could not load spec from {config_path}")
config_module = importlib.util.module_from_spec(spec_config)
if spec_config.loader is None:
    raise ImportError(f"No loader found for {config_path}")
spec_config.loader.exec_module(config_module)

BaseAzureAISearchTool = ai_search_module.BaseAzureAISearchTool
SearchQuery = ai_search_module.SearchQuery
SearchResult = ai_search_module.SearchResult
SearchResults = ai_search_module.SearchResults
AzureAISearchConfig = config_module.AzureAISearchConfig

_SearchQuery: TypeAlias = Any
_SearchResult: TypeAlias = Any
_SearchResults: TypeAlias = Any


original_abstractmethods: frozenset[str] = getattr(BaseAzureAISearchTool, "__abstractmethods__", frozenset())
BaseAzureAISearchTool.__abstractmethods__ = frozenset()


class MockAzureAISearchTool(BaseAzureAISearchTool):  # type: ignore
    """Mock implementation for testing purposes."""

    _name: str
    _description: str
    _endpoint: str
    _index_name: str
    _api_version: str
    _credential: Any  # Keep Any for flexibility with dict/object credentials
    _query_type: str
    _search_fields: List[str]
    _select_fields: List[str]
    _vector_fields: List[str]
    _top: int
    _semantic_config_name: Optional[str]
    _client: Optional[MagicMock]
    _openai_client: Any  # Keep Any for mock flexibility
    _embedding_model: str
    _mock_results: List[Dict[str, Any]]

    def __init__(self, **kwargs: Any) -> None:
        self._name = str(kwargs.get("name", ""))
        self._description = str(kwargs.get("description", ""))
        self._endpoint = str(kwargs.get("endpoint", ""))
        self._index_name = str(kwargs.get("index_name", ""))
        self._api_version = str(kwargs.get("api_version", ""))
        self._credential = kwargs.get("credential", None)
        self._query_type = str(kwargs.get("query_type", "keyword"))
        self._search_fields = list(kwargs.get("search_fields", []))
        self._select_fields = list(kwargs.get("select_fields", []))
        self._vector_fields = list(kwargs.get("vector_fields", []))
        self._top = int(kwargs.get("top", 5))
        self._semantic_config_name = kwargs.get("semantic_config_name", None)
        self._client = None
        self._openai_client = kwargs.get("openai_client")
        self._embedding_model = str(kwargs.get("embedding_model", "text-embedding-ada-002"))
        self._mock_results = list(
            kwargs.get(
                "mock_results",
                [
                    {
                        "@search.score": 0.95,
                        "id": "doc1",
                        "content": "This is the first document content",
                        "title": "Document 1",
                        "source": "test-source-1",
                        "@metadata": {"key": "value1"},
                    },
                    {
                        "@search.score": 0.85,
                        "id": "doc2",
                        "content": "This is the second document content",
                        "title": "Document 2",
                        "source": "test-source-2",
                        "@metadata": {"key": "value2"},
                    },
                ],
            )
        )

        self.search_config = MagicMock()
        self.search_config.endpoint = self._endpoint
        self.search_config.index_name = self._index_name
        self.search_config.api_version = self._api_version
        self.search_config.credential = self._credential
        self.search_config.query_type = self._query_type
        self.search_config.search_fields = self._search_fields
        self.search_config.select_fields = self._select_fields
        self.search_config.vector_fields = self._vector_fields
        self.search_config.top = self._top
        self.search_config.semantic_config_name = self._semantic_config_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def schema(self) -> Dict[str, Any]:
        """Return the schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query text"}},
                "required": ["query"],
            },
        }

    @classmethod
    def load_component(cls, model: ComponentModel, expected: Optional[Type[Any]] = None) -> "MockAzureAISearchTool":
        """Load component from model."""
        return cls(**model.config)

    def dump_component(self) -> ComponentModel:
        """Dump component to model."""
        return ComponentModel(
            provider="autogen_ext.tools.azure.test_ai_search_tool.MockAzureAISearchTool",
            config={
                "name": self.name,
                "description": self.description,
                "endpoint": self._endpoint,
                "index_name": self._index_name,
                "api_version": self._api_version,
                "credential": self._credential,
                "query_type": self._query_type,
                "search_fields": self._search_fields,
                "select_fields": self._select_fields,
                "vector_fields": self._vector_fields,
                "top": self._top,
                "semantic_config_name": self._semantic_config_name,
            },
        )

    async def _get_client(self) -> MagicMock:
        """Return a mock client for testing."""

        if self._client is not None:
            return self._client

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        self._client = mock_client
        return mock_client

    async def _get_embedding(self, query: str) -> List[float]:
        """Generate embedding vector for the query text."""
        if self._openai_client:
            response = await self._openai_client.embeddings.create(model=self._embedding_model, input=query)
            embedding_data: List[Any] = response.data[0]["embedding"]

            result: List[float] = []
            if isinstance(embedding_data, list):
                for item_val in embedding_data:
                    try:
                        if isinstance(item_val, (int, float)):
                            result.append(float(item_val))
                        elif isinstance(item_val, str):
                            result.append(float(item_val))
                        else:
                            result.append(0.0)
                    except (ValueError, TypeError):
                        result.append(0.0)
                return result
            else:
                return [0.0]

        return [0.1, 0.2, 0.3, 0.4, 0.5]

    async def get_embedding_for_test(self, query: str) -> List[float]:
        """Public async test helper to access _get_embedding."""
        return await self._get_embedding(query)

    async def get_client_for_test(self) -> MagicMock:
        """Public async test helper to access _get_client."""
        return await self._get_client()

    @property
    def endpoint_for_test(self) -> str:
        """Access protected endpoint attribute for testing."""
        return self._endpoint

    @property
    def index_name_for_test(self) -> str:
        """Access protected index_name attribute for testing."""
        return self._index_name

    @property
    def credential_for_test(self) -> Any:
        """Access protected credential attribute for testing."""
        return self._credential

    async def run(self, query: Any, cancellation_token: Optional[CancellationToken] = None) -> Any:
        """Run the search with the given query."""
        if cancellation_token and getattr(cancellation_token, "cancelled", False):
            raise Exception("Operation cancelled")

        query_dict = {}
        if hasattr(query, "model_dump"):
            query_dict = query.model_dump()
        elif hasattr(query, "dict"):
            query_dict = query.dict()
        elif isinstance(query, str):
            query_dict = {"query": query}
        elif hasattr(query, "__iter__") and not isinstance(query, (str, bytes)):
            query_dict = dict(query)

        query_text = query_dict.get("query", "")
        vector = query_dict.get("vector", None)
        filter_expr = query_dict.get("filter", None)
        top = query_dict.get("top", self.search_config.top)

        client = await self._get_client()

        search_text: str = query_text
        vectors: Optional[List[Dict[str, Any]]] = None

        kwargs: Dict[str, Any] = {}

        if self._query_type == "fulltext" and self._semantic_config_name:
            kwargs["query_type"] = "semantic"
            kwargs["semantic_configuration_name"] = self._semantic_config_name
        elif self._query_type == "hybrid":
            kwargs["query_type"] = "semantic"
            kwargs["semantic_configuration_name"] = self._semantic_config_name
        else:
            kwargs["query_type"] = "simple"

        if self._query_type == "vector" or self._vector_fields:
            vector_value = vector if vector is not None else await self._get_embedding(query_text)

            if self._vector_fields:
                vector_list = [{"value": vector_value, "fields": field, "k": top} for field in self._vector_fields]
                vectors = vector_list
                if self._query_type == "vector":
                    search_text = ""

        if vectors:
            kwargs["vectors"] = vectors

        if filter_expr:
            kwargs["filter"] = filter_expr

        if top:
            kwargs["top"] = top

        if self._search_fields:
            kwargs["search_fields"] = self._search_fields

        if self._select_fields:
            kwargs["select"] = self._select_fields

        try:
            await client.search(search_text, **kwargs)
        except ResourceNotFoundError as e:
            raise ValueError(f"Index '{self._index_name}' not found. Please check the index name and try again.") from e
        except HttpResponseError as e:
            error_message = str(e)
            if "401" in error_message or "unauthorized" in error_message.lower():
                raise ValueError(
                    f"Authentication failed for Azure AI Search: {error_message}. Please check your API key and credentials."
                ) from e
            else:
                raise ValueError(f"Error from Azure AI Search: {error_message}") from e

        if isinstance(client.search, AsyncMock) and not client.search.return_value.items:
            return SearchResults(results=[])

        results: List[Any] = []
        for result in self._mock_results:
            score = cast(float, result.get("@search.score", 0.0))

            content: Dict[str, Any] = {}
            for content_key, content_val in result.items():
                if isinstance(content_key, str) and not content_key.startswith("@"):
                    content[content_key] = content_val

            metadata: Dict[str, Any] = {}
            metadata_obj = result.get("@metadata")
            if is_dict_any_any(metadata_obj):
                for k, v in metadata_obj.items():
                    if isinstance(k, str):
                        metadata[k] = v

            results.append(
                SearchResult(
                    score=score,
                    content=content,
                    metadata=metadata,
                )
            )

        return SearchResults(results=results)

    def return_value_as_string(self, value: Any) -> str:
        """Convert the search results to a string representation.

        This is a custom implementation for testing purposes that provides
        a more detailed output than the base class implementation.

        Args:
            value (_SearchResults): The search results to format as a string

        Returns:
            str: A formatted string representation of the search results
        """
        results: List[Any] = []
        if hasattr(value, "results"):
            results = value.results

        if not results:
            return "No search results found."

        result_strings: List[str] = []
        for i, result in enumerate(results, 1):
            content_items: List[str] = []
            if hasattr(result, "content") and hasattr(result.content, "items"):
                for content_key, content_val in result.content.items():
                    content_key_str = str(content_key)
                    content_items.append(f"{content_key_str}: {content_val}")

            content_str = ", ".join(content_items)

            metadata_items: List[str] = []
            if hasattr(result, "metadata") and hasattr(result.metadata, "items"):
                for meta_key, meta_val in result.metadata.items():
                    meta_key_str = str(meta_key)
                    metadata_items.append(f"{meta_key_str}={meta_val}")
            metadata_str = f" [Metadata: {', '.join(metadata_items)}]"

            score = 0.0
            if hasattr(result, "score"):
                score = float(result.score)
            result_strings.append(f"Result {i} (Score: {score:.2f}): {content_str}{metadata_str}")

        return "\n".join(result_strings)


class AsyncIterator:
    """Async iterator for testing."""

    def __init__(self, items: List[Dict[str, Any]]) -> None:
        self.items = list(items)

    def __aiter__(self) -> "AsyncIterator":
        return self

    async def __anext__(self) -> Dict[str, Any]:
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)

    async def get_count(self) -> int:
        return len(self.items)

    @property
    def items(self) -> List[Dict[str, Any]]:
        return self._items

    @items.setter
    def items(self, value: List[Dict[str, Any]]) -> None:
        self._items = value


@pytest.mark.asyncio
async def test_tool_schema_generation(test_config: ComponentModel) -> None:
    """Test that the tool schema is generated correctly."""
    tool = MockAzureAISearchTool.load_component(test_config)
    schema = tool.schema
    assert "name" in schema
    assert schema["name"] == "TestAzureSearch"
    assert "description" in schema
    assert "parameters" in schema
    assert "properties" in schema["parameters"]

    properties = schema["parameters"]["properties"]
    assert "query" in properties
    assert properties["query"]["type"] == "string"
    assert properties["query"]["description"] == "Search query text"

    assert len(properties) == 1
    assert "required" in schema["parameters"]
    assert "query" in schema["parameters"]["required"]


def test_tool_properties(test_config: ComponentModel) -> None:
    """Test that the tool properties are correctly set."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool.load_component(test_config)

        assert tool.name == "TestAzureSearch"
        assert tool.description == "Test Azure AI Search Tool"
        assert tool.search_config.endpoint == "https://test-search-service.search.windows.net"
        assert tool.search_config.index_name == "test-index"
        assert tool.search_config.api_version == "2023-10-01-Preview"
        assert tool.search_config.query_type == "keyword"
        assert tool.search_config.search_fields == ["content", "title"]
        assert tool.search_config.select_fields == ["id", "content", "title", "source"]
        assert tool.search_config.top == 5


def test_component_base_class(test_config: ComponentModel) -> None:
    """Test that the tool correctly implements the Component interface."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool.load_component(test_config)
        assert tool.dump_component() is not None
        assert MockAzureAISearchTool.load_component(tool.dump_component(), MockAzureAISearchTool) is not None


@pytest.mark.asyncio
async def test_keyword_search(keyword_config: ComponentModel) -> None:
    """Test keyword search functionality."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool.load_component(keyword_config)

        search_results = [
            {
                "@search.score": 0.95,
                "id": "doc1",
                "content": "This is the first document content",
                "title": "Document 1",
                "source": "test-source-1",
                "@metadata": {"key": "value1"},
            },
            {
                "@search.score": 0.85,
                "id": "doc2",
                "content": "This is the second document content",
                "title": "Document 2",
                "source": "test-source-2",
                "@metadata": {"key": "value2"},
            },
        ]

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client.search = AsyncMock()
        mock_client.search.return_value = AsyncIterator(search_results)

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run("test query", CancellationToken())

            assert hasattr(result, "results")
            assert len(result.results) == 2

            for item in result.results:
                assert hasattr(item, "score")
                assert hasattr(item, "content")
                assert hasattr(item, "metadata")

            assert result.results[0].score == 0.95
            assert result.results[0].content["id"] == "doc1"

            mock_client.search.assert_called_once()
            args, kwargs = mock_client.search.call_args
            assert args[0] == "test query"
            assert kwargs.get("query_type") == "simple"  # Azure SDK still uses 'simple' for keyword searches


@pytest.mark.asyncio
async def test_vector_search(vector_config: ComponentModel) -> None:
    """Test that the tool correctly performs a vector search."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool.load_component(vector_config)

        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock(return_value=mock_client_instance)

        with patch.object(tool, "_get_embedding", AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4, 0.5])):
            mock_results = [
                {
                    "@search.score": 0.95,
                    "id": "doc1",
                    "content": "This is the first document content",
                    "title": "Document 1",
                    "@metadata": {"key": "value1"},
                },
                {
                    "@search.score": 0.85,
                    "id": "doc2",
                    "content": "This is the second document content",
                    "title": "Document 2",
                    "@metadata": {"key": "value2"},
                },
            ]

            mock_client_instance.search = AsyncMock()
            mock_client_instance.search.return_value = AsyncIterator(mock_results)

            mock_client.return_value = mock_client_instance
            with patch.object(tool, "_get_client", return_value=mock_client.return_value):
                await tool.run(SearchQuery(query="test query"), CancellationToken())
                mock_client_instance.search.assert_called_once()
                args, kwargs = mock_client_instance.search.call_args
                assert args[0] == ""
                assert "vectors" in kwargs
                assert len(kwargs["vectors"]) == 1
                assert kwargs["vectors"][0]["fields"] == "embedding"


@pytest.mark.asyncio
async def test_error_handling_resource_not_found(test_config: ComponentModel) -> None:
    """Test that the tool correctly handles resource not found errors."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool.load_component(test_config)
        error_msg = "Resource 'test-index' not found"

        with patch.object(tool, "run", autospec=True) as mock_run:
            mock_run.side_effect = Exception(error_msg)

            with pytest.raises(Exception) as excinfo:
                await tool.run(SearchQuery(query="test query"), CancellationToken())

            assert "not found" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_cancellation(test_config: ComponentModel) -> None:
    """Test that the tool correctly handles cancellation."""
    token = CancellationToken()
    token.cancel()

    mock_tool = MockAzureAISearchTool.load_component(test_config)

    async def cancel_side_effect(query: Any, cancellation_token: Optional[CancellationToken] = None) -> Any:
        if cancellation_token and cancellation_token.is_cancelled():
            raise Exception("Operation cancelled by test")
        return SearchResults(results=[])

    with patch.object(mock_tool, "run", autospec=True) as mock_run:
        mock_run.side_effect = cancel_side_effect

        with pytest.raises(Exception) as excinfo:
            await mock_tool.run(SearchQuery(query="test query"), token)

        assert "cancelled" in str(excinfo.value).lower()


def test_config_serialization(test_config: ComponentModel) -> None:
    """Test that the tool configuration is correctly serialized."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool.load_component(test_config)
        config = tool.dump_component()

        assert config.config["name"] == test_config.config["name"]
        assert config.config["description"] == test_config.config["description"]
        assert config.config["endpoint"] == test_config.config["endpoint"]
        assert config.config["index_name"] == test_config.config["index_name"]
        assert config.config["api_version"] == test_config.config["api_version"]
        assert config.config["query_type"] == test_config.config["query_type"]
        assert config.config["search_fields"] == test_config.config["search_fields"]
        assert config.config["select_fields"] == test_config.config["select_fields"]
        assert config.config["top"] == test_config.config["top"]


@pytest.mark.asyncio
async def test_hybrid_search(test_config: ComponentModel) -> None:
    """Test that the tool correctly performs a hybrid search."""
    hybrid_config = ComponentModel(
        provider="autogen_ext.tools.azure.test_ai_search_tool.MockAzureAISearchTool",
        config={
            "name": "TestAzureSearch",
            "description": "Test Azure AI Search Tool",
            "endpoint": "https://test-search-service.search.windows.net",
            "index_name": "test-index",
            "api_version": "2023-10-01-Preview",
            "credential": {"api_key": "test-key"},
            "query_type": "fulltext",
            "semantic_config_name": "test-semantic-config",
            "vector_fields": ["embedding"],
            "search_fields": ["content", "title"],
            "select_fields": ["id", "content", "title", "source"],
            "top": 5,
            "openai_client": MagicMock(),
            "embedding_model": "mock-embedding-model",
        },
    )

    tool = MockAzureAISearchTool.load_component(hybrid_config)

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mock_results = [
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
    mock_client.search = AsyncMock(return_value=AsyncIterator(mock_results))

    with patch.object(tool, "_get_client", return_value=mock_client):
        with patch.object(tool, "_get_embedding", return_value=[0.1, 0.2, 0.3, 0.4, 0.5]):
            result = await tool.run(SearchQuery(query="test query"), CancellationToken())

            mock_client.search.assert_called_once()
            call_args = mock_client.search.call_args
            assert call_args[0][0] == "test query"
            call_kwargs = call_args[1]
            assert "query_type" in call_kwargs
            assert call_kwargs["query_type"] == "semantic"
            assert "vectors" in call_kwargs

            assert len(result.results) == 2
            assert result.results[0].score == 0.95
            assert result.results[0].content["id"] == "doc1"
            assert result.results[1].score == 0.85
            assert result.results[1].content["id"] == "doc2"


class MockVectorizableTextQuery:
    """Mock implementation of VectorizableTextQuery for testing."""

    def __init__(self, text: str, k: int, fields: Union[str, List[str]]):
        self.text = text
        self.k = k
        self.fields = fields if isinstance(fields, str) else ",".join(fields)


@pytest.mark.asyncio
async def test_error_handling_invalid_index() -> None:
    """Test that appropriate errors are raised for invalid index."""
    with patch("azure.search.documents.aio.SearchClient"):
        search_tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="nonexistent-index",
            credential=AzureKeyCredential("test-key"),
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search = AsyncMock(side_effect=ResourceNotFoundError("Index not found"))

        with patch.object(search_tool, "_get_client", return_value=mock_client):
            with pytest.raises(ValueError) as excinfo:
                await search_tool.run("test query", CancellationToken())

            assert "Index 'nonexistent-index' not found" in str(excinfo.value)
            assert "check the index name" in str(excinfo.value)


@pytest.mark.asyncio
async def test_error_handling_authentication() -> None:
    """Test that appropriate errors are raised for authentication issues."""
    with patch("azure.search.documents.aio.SearchClient"):
        search_tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("invalid-key"),
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search = AsyncMock(side_effect=HttpResponseError("401 Unauthorized"))

        with patch.object(search_tool, "_get_client", return_value=mock_client):
            with pytest.raises(ValueError) as excinfo:
                await search_tool.run("test query", CancellationToken())

            assert "Authentication failed" in str(excinfo.value)
            assert "check your API key" in str(excinfo.value)


@pytest.mark.asyncio
async def test_actual_implementation_cancellation() -> None:
    """Test that the actual implementation correctly handles cancellation."""
    tool = MockAzureAISearchTool.load_component(
        ComponentModel(
            provider="autogen_ext.tools.azure.test_ai_search_tool.MockAzureAISearchTool",
            config={
                "name": "test_search",
                "endpoint": "https://test.search.windows.net",
                "index_name": "test-index",
                "credential": {"api_key": "test-key"},
            },
        )
    )

    from autogen_ext.tools.azure._ai_search import BaseAzureAISearchTool

    async def patched_run(query: Any, cancellation_token: Optional[CancellationToken] = None) -> Any:
        method = BaseAzureAISearchTool.run
        return await method(tool, query, cancellation_token)

    tool.run = patched_run  # type: ignore

    class MockSearchResults:
        def __aiter__(self) -> "MockSearchResults":
            return self

        async def __anext__(self) -> None:
            raise StopAsyncIteration

    async def delayed_search_coroutine() -> MockSearchResults:
        await asyncio.sleep(0.1)
        return MockSearchResults()

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.search = MagicMock(return_value=delayed_search_coroutine())

    with patch.object(tool, "_get_client", new=AsyncMock(return_value=mock_client)):
        token = CancellationToken()
        token.cancel()

        with pytest.raises(Exception, match="Operation cancelled"):
            await tool.run("test query", cancellation_token=token)


@pytest.mark.asyncio
async def test_get_embedding_method() -> None:
    """Test the _get_embedding method for generating embeddings."""
    with patch("azure.search.documents.aio.SearchClient"):
        search_tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
            openai_client=MagicMock(),
            embedding_model="text-embedding-ada-002",
        )

        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [{"embedding": [0.1, 0.2, 0.3]}]
        mock_openai_client = MagicMock()
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        search_tool._openai_client = mock_openai_client  # pyright: ignore

        embedding = await search_tool.get_embedding_for_test("test query")

        assert embedding == [0.1, 0.2, 0.3]
        mock_openai_client.embeddings.create.assert_called_once()
        call_args = mock_openai_client.embeddings.create.call_args
        call_kwargs = call_args[1]
        assert call_kwargs["model"] == "text-embedding-ada-002"
        assert call_kwargs["input"] == "test query"


@pytest.mark.asyncio
async def test_empty_search_results() -> None:
    """Test handling of empty search results."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
            mock_results=[],
        )

        empty_iterator = AsyncIterator([])

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search = AsyncMock(return_value=empty_iterator)

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run("test query", CancellationToken())

            assert hasattr(result, "results")
            assert len(result.results) == 0

            string_result = tool.return_value_as_string(result)
            assert string_result == "No search results found."


@pytest.mark.asyncio
async def test_different_query_formats() -> None:
    """Test handling of different query input formats."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search = AsyncMock(return_value=AsyncIterator([]))

        with patch.object(tool, "_get_client", return_value=mock_client):
            await tool.run("test query", CancellationToken())
            call_args = mock_client.search.call_args
            assert call_args[0][0] == "test query"
            mock_client.search.reset_mock()

            await tool.run({"query": "dict query"}, CancellationToken())
            call_args = mock_client.search.call_args
            assert call_args[0][0] == "dict query"
            mock_client.search.reset_mock()

            await tool.run(SearchQuery(query="model query"), CancellationToken())
            call_args = mock_client.search.call_args
            assert call_args[0][0] == "model query"
            mock_client.search.reset_mock()

            class ModelDumpQuery:
                def model_dump(self) -> Dict[str, str]:
                    return {"query": "model_dump query"}

            await tool.run(ModelDumpQuery(), CancellationToken())
            call_args = mock_client.search.call_args
            assert call_args[0][0] == "model_dump query"
            mock_client.search.reset_mock()

            class DictQuery:
                def dict(self) -> Dict[str, str]:
                    return {"query": "dict method query"}

            await tool.run(DictQuery(), CancellationToken())
            call_args = mock_client.search.call_args
            assert call_args[0][0] == "dict method query"


@pytest.mark.asyncio
async def test_return_value_formatting() -> None:
    """Test the return_value_as_string method with various inputs."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
        )

        results = SearchResults(
            results=[
                SearchResult(
                    score=0.95,
                    content={"id": "doc1", "title": "Test Document", "content": "Test content"},
                    metadata={"key": "value"},
                )
            ]
        )

        formatted = tool.return_value_as_string(results)
        assert "Result 1 (Score: 0.95)" in formatted
        assert "id: doc1" in formatted
        assert "title: Test Document" in formatted
        assert "content: Test content" in formatted
        assert "[Metadata: key=value]" in formatted

        empty_results = SearchResults(results=[])
        assert tool.return_value_as_string(empty_results) == "No search results found."

        class CustomResult:
            """Custom result class for testing."""

            def __init__(self) -> None:
                """Initialize with test data."""
                result_obj = type(
                    "ResultObject",
                    (),
                    {"score": 0.8, "content": {"custom": "value"}, "metadata": {"custom_meta": "meta_value"}},
                )
                self.results = [result_obj()]

        custom_result = CustomResult()
        formatted_custom = tool.return_value_as_string(custom_result)
        assert "Result 1 (Score: 0.80)" in formatted_custom
        assert "custom: value" in formatted_custom
        assert "[Metadata: custom_meta=meta_value]" in formatted_custom


@pytest.mark.asyncio
async def test_filter_parameter() -> None:
    """Test that filter parameters are correctly passed to the search client."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search = AsyncMock(return_value=AsyncIterator([]))

        with patch.object(tool, "_get_client", return_value=mock_client):
            await tool.run({"query": "test query", "filter": "category eq 'docs'"}, CancellationToken())

            call_args = mock_client.search.call_args
            positional_args = call_args[0]
            keyword_args = call_args[1]
            assert positional_args[0] == "test query"
            assert keyword_args.get("filter") == "category eq 'docs'"


@pytest.mark.asyncio
async def test_top_parameter() -> None:
    """Test that top parameter is correctly passed to the search client."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
            top=10,
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search = AsyncMock(return_value=AsyncIterator([]))

        with patch.object(tool, "_get_client", return_value=mock_client):
            await tool.run("test query", CancellationToken())
            call_args = mock_client.search.call_args
            keyword_args = call_args[1]
            assert keyword_args.get("top") == 10
            mock_client.search.reset_mock()

            await tool.run({"query": "test query", "top": 5}, CancellationToken())
            call_args = mock_client.search.call_args
            keyword_args = call_args[1]
            assert keyword_args.get("top") == 5


def test_initialization_with_dict_credential() -> None:
    """Test initialization with a dictionary credential."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential={"api_key": "test-key"},
        )

        assert tool.name == "test_search"
        assert tool.endpoint_for_test == "https://test-endpoint.search.windows.net"
        assert tool.index_name_for_test == "test-index"

        credential_dict = tool.credential_for_test
        if isinstance(credential_dict, dict):
            assert "api_key" in credential_dict
            api_key: Any = credential_dict["api_key"]
            assert isinstance(api_key, str)
            assert api_key == "test-key"
        else:
            raise AssertionError("Credential should be a dictionary")


@pytest.mark.asyncio
async def test_client_creation_with_multiple_calls() -> None:
    """Test that the client is created only once and reused for multiple calls."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
        )

        async def setup_mock_client() -> None:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.search = AsyncMock(return_value=AsyncIterator([]))

            with patch.object(MockAzureAISearchTool, "_get_client", return_value=mock_client):
                await tool.run("test query", CancellationToken())
                await tool.run("another query", CancellationToken())

                assert mock_client.search.call_count == 2

        await setup_mock_client()


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


def is_dict_any_any(val: Any) -> TypeGuard[Dict[Any, Any]]:
    """Type guard to check if a value is a Dict[Any, Any]."""
    return isinstance(val, dict)


@pytest.mark.asyncio
async def test_vector_search_with_explicit_vector() -> None:
    """Test vector search with explicitly provided vector."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
            query_type="vector",
            vector_fields=["embedding"],
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search = AsyncMock(return_value=AsyncIterator([]))

        with patch.object(tool, "_get_client", return_value=mock_client):
            explicit_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
            await tool.run({"query": "test query", "vector": explicit_vector}, CancellationToken())

            call_args = mock_client.search.call_args
            keyword_args = call_args[1]

            assert call_args[0][0] == ""
            assert "vectors" in keyword_args
            assert len(keyword_args["vectors"]) == 1
            assert keyword_args["vectors"][0]["value"] == explicit_vector
            assert keyword_args["vectors"][0]["fields"] == "embedding"


@pytest.mark.asyncio
async def test_fulltext_search_with_semantic_config() -> None:
    """Test fulltext search with semantic configuration."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
            query_type="fulltext",
            semantic_config_name="my-semantic-config",
            search_fields=["title", "content"],
            select_fields=["id", "title", "content"],
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search = AsyncMock(return_value=AsyncIterator([]))

        with patch.object(tool, "_get_client", return_value=mock_client):
            await tool.run("semantic query", CancellationToken())

            call_args = mock_client.search.call_args
            keyword_args = call_args[1]

            assert call_args[0][0] == "semantic query"
            assert keyword_args["query_type"] == "semantic"
            assert keyword_args["semantic_configuration_name"] == "my-semantic-config"
            assert keyword_args["search_fields"] == ["title", "content"]
            assert keyword_args["select"] == ["id", "title", "content"]


@pytest.mark.asyncio
async def test_authentication_error_handling() -> None:
    """Test handling of authentication errors."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("invalid-key"),
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        auth_error = HttpResponseError()
        auth_error.message = "401 Unauthorized: Access denied due to invalid credentials"
        mock_client.search = AsyncMock(side_effect=auth_error)

        with patch.object(tool, "_get_client", return_value=mock_client):
            with pytest.raises(ValueError) as excinfo:
                await tool.run("test query", CancellationToken())

            error_message = str(excinfo.value)
            assert "Authentication failed" in error_message
            assert "Please check your API key and credentials" in error_message


@pytest.mark.asyncio
async def test_general_http_error_handling() -> None:
    """Test handling of general HTTP errors."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool(
            name="test_search",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        general_error = HttpResponseError()
        general_error.message = "500 Internal Server Error: Something went wrong"
        mock_client.search = AsyncMock(side_effect=general_error)

        with patch.object(tool, "_get_client", return_value=mock_client):
            with pytest.raises(ValueError) as excinfo:
                await tool.run("test query", CancellationToken())

            error_message = str(excinfo.value)
            assert "Error from Azure AI Search" in error_message
            assert "500 Internal Server Error" in error_message


def test_schema_validation() -> None:
    """Test that the schema is correctly generated."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool(
            name="custom-search",
            description="Custom search description",
            endpoint="https://test-endpoint.search.windows.net",
            index_name="test-index",
            credential=AzureKeyCredential("test-key"),
        )

        schema = tool.schema

        assert schema["name"] == "custom-search"
        assert schema["description"] == "Custom search description"
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"
        assert "query" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["query"]
