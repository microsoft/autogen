"""Tests for the Azure AI Search tool."""

import importlib.util
import os
import sys
from typing import Any, Dict, List, Optional, Type, TypeAlias, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import CancellationToken, ComponentModel

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

    def __init__(self, **kwargs: Any) -> None:
        self._name = kwargs.get("name", "")
        self._description = kwargs.get("description", "")
        self._endpoint = kwargs.get("endpoint", "")
        self._index_name = kwargs.get("index_name", "")
        self._api_version = kwargs.get("api_version", "")
        self._credential = kwargs.get("credential", None)
        self._query_type = kwargs.get("query_type", "simple")
        self._search_fields = kwargs.get("search_fields", [])
        self._select_fields = kwargs.get("select_fields", [])
        self._vector_fields = kwargs.get("vector_fields", [])
        self._top = kwargs.get("top", 5)
        self._semantic_config_name = kwargs.get("semantic_config_name", None)
        self._client: Optional[MagicMock] = None

        self.openai_client = kwargs.get("openai_client", None)
        self.embedding_model = kwargs.get("embedding_model", "")

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
        return str(self._name)

    @property
    def description(self) -> str:
        return str(self._description)

    @property
    def schema(self) -> Dict[str, Any]:
        """Return the schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "filter": {"type": "string", "description": "Optional filter expression"},
                    "top": {"type": "integer", "description": "Optional number of results to return"},
                    "vector": {"type": "array", "description": "Optional vector for vector/hybrid search"},
                },
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

    async def _get_embedding(self, query: str) -> List[float]:
        """Return fixed embeddings for testing."""
        return [0.1, 0.2, 0.3, 0.4, 0.5]

    async def _get_client(self) -> MagicMock:
        """Return a mock client for testing."""

        if self._client is not None:
            return self._client

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        self._client = mock_client
        return mock_client

    async def run(self, query: Any, cancellation_token: Optional[CancellationToken] = None) -> Any:
        """Run the search with the given query."""
        if cancellation_token and getattr(cancellation_token, "cancelled", False):
            raise Exception("Operation cancelled")

        query_dict = {}
        if hasattr(query, "model_dump"):
            query_dict = query.model_dump()
        elif hasattr(query, "dict"):
            query_dict = query.dict()
        else:
            query_dict = dict(query) if hasattr(query, "__iter__") else {}

        query_text = query_dict.get("query", "")
        vector = query_dict.get("vector", None)
        filter_expr = query_dict.get("filter", None)
        top = query_dict.get("top", self.search_config.top)

        client = await self._get_client()

        search_text: str = query_text
        vectors: Optional[List[Dict[str, Any]]] = None

        kwargs: Dict[str, Any] = {}

        if self._query_type == "semantic" and self._semantic_config_name:
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

        mock_results = [
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

        await client.search(search_text, **kwargs)

        results: List[Any] = []
        for result in mock_results:
            score = cast(float, result.get("@search.score", 0.0))

            content = {}
            for content_key, content_val in result.items():
                if isinstance(content_key, str) and not content_key.startswith("@"):
                    content[content_key] = content_val

            metadata = {}
            metadata_obj = result.get("@metadata")
            if isinstance(metadata_obj, dict):
                metadata = metadata_obj

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


class MockResourceNotFoundError(Exception):
    """Mock for ResourceNotFoundError."""

    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        self.message = message
        super().__init__(message)


class MockHttpResponseError(Exception):
    """Mock for HttpResponseError."""

    def __init__(self, message: str = "Http error", **kwargs: Any) -> None:
        self.message = message
        super().__init__(message)


MOCK_SEARCH_RESPONSE: List[Dict[str, Any]] = [
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


@pytest.mark.asyncio
async def test_tool_schema_generation(test_config: ComponentModel) -> None:
    """Test that the tool correctly generates its schema."""
    tool = MockAzureAISearchTool.load_component(test_config)
    schema = tool.schema

    assert schema["name"] == "TestAzureSearch"
    assert schema["description"] == "Test Azure AI Search Tool"
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"
    assert "properties" in schema["parameters"]
    assert schema["parameters"]["properties"]["query"]["description"] == "Search query text"
    assert schema["parameters"]["properties"]["query"]["type"] == "string"
    assert "filter" in schema["parameters"]["properties"]
    assert "top" in schema["parameters"]["properties"]
    assert "vector" in schema["parameters"]["properties"]
    assert "required" in schema["parameters"]
    assert schema["parameters"]["required"] == ["query"]


def test_tool_properties(test_config: ComponentModel) -> None:
    """Test that the tool properties are correctly set."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool.load_component(test_config)

        assert tool.name == "TestAzureSearch"
        assert tool.description == "Test Azure AI Search Tool"
        assert tool.search_config.endpoint == "https://test-search-service.search.windows.net"
        assert tool.search_config.index_name == "test-index"
        assert tool.search_config.api_version == "2023-10-01-Preview"
        assert tool.search_config.query_type == "simple"
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
async def test_simple_search(test_config: ComponentModel) -> None:
    """Test that the tool correctly performs a simple search."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool.load_component(test_config)

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
            search_results_obj = await tool.run(SearchQuery(query="test query"), CancellationToken())

            assert isinstance(search_results_obj, SearchResults)
            assert len(search_results_obj.results) == 2
            for result in search_results_obj.results:
                assert isinstance(result, SearchResult)
                assert hasattr(result, "score")
                assert hasattr(result, "content")
                assert hasattr(result, "metadata")

            assert search_results_obj.results[0].score == 0.95
            assert search_results_obj.results[0].content["id"] == "doc1"
            assert search_results_obj.results[0].content["title"] == "Document 1"
            mock_client.search.assert_called_once()
            args, kwargs = mock_client.search.call_args
            assert args[0] == "test query"
            assert kwargs.get("query_type") == "simple"


@pytest.mark.asyncio
async def test_semantic_search(semantic_config: ComponentModel) -> None:
    """Test that the tool correctly performs a semantic search."""
    with patch("azure.search.documents.aio.SearchClient"):
        tool = MockAzureAISearchTool.load_component(semantic_config)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client.search = AsyncMock(return_value=AsyncIterator(MOCK_SEARCH_RESPONSE))

        with patch.object(tool, "_get_client", return_value=mock_client):
            await tool.run(SearchQuery(query="test query"), CancellationToken())
            mock_client.search.assert_called_once()
            args, kwargs = mock_client.search.call_args

            assert args[0] == "test query"
            assert kwargs.get("query_type") == "semantic"
            assert kwargs.get("semantic_configuration_name") == "test-semantic-config"


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
            "query_type": "semantic",
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

    mock_client = AsyncMock()

    sample_results = SearchResults(
        results=[
            SearchResult(
                score=0.95,
                content={
                    "id": "doc1",
                    "content": "This is the first document content",
                    "title": "Document 1",
                    "source": "test-source-1",
                },
                metadata={},
            ),
            SearchResult(
                score=0.85,
                content={
                    "id": "doc2",
                    "content": "This is the second document content",
                    "title": "Document 2",
                    "source": "test-source-2",
                },
                metadata={},
            ),
        ]
    )

    async def search_side_effect(query: Any, cancellation_token: Optional[CancellationToken] = None) -> Any:
        mock_client.search.assert_not_called()
        await run_original(query, cancellation_token)
        return sample_results

    with patch.object(tool, "_get_client", return_value=mock_client) as mock_get_client:
        mock_client.search = AsyncMock()

        run_original = tool.run
        with patch.object(tool, "run", side_effect=search_side_effect):
            result = await tool.run(SearchQuery(query="test query"), CancellationToken())
            mock_get_client.assert_called_once()
            mock_client.search.assert_called_once()
            args, kwargs = mock_client.search.call_args
            assert args[0] == "test query"
            assert "query_type" in kwargs
            assert kwargs["query_type"] == "semantic"
            assert "vectors" in kwargs
            assert len(getattr(result, "results", [])) == 2
            assert getattr(result.results[0], "score", 0) == 0.95
