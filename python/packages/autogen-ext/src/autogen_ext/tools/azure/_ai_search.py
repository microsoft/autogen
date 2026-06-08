from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from contextvars import ContextVar
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Union,
)

from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool, ToolSchema
from pydantic import BaseModel, Field

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.search.documents.aio import SearchClient

from ._config import (
    DEFAULT_API_VERSION,
    AzureAISearchConfig,
)

SearchDocument = Dict[str, Any]
MetadataDict = Dict[str, Any]
ContentDict = Dict[str, Any]

if TYPE_CHECKING:
    from azure.search.documents.aio import AsyncSearchItemPaged

    SearchResultsIterable = AsyncSearchItemPaged[SearchDocument]
else:
    SearchResultsIterable = Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from azure.search.documents.models import (
        VectorizableTextQuery,
        VectorizedQuery,
        VectorQuery,
    )

try:
    from azure.search.documents.models import VectorizableTextQuery, VectorizedQuery, VectorQuery

    has_azure_search = True
except ImportError:
    has_azure_search = False
    logger.error(
        "The 'azure-search-documents' package is required for this tool but was not found. "
        "Please install it with: uv add install azure-search-documents"
    )


if TYPE_CHECKING:
    from typing import Protocol

    class SearchClientProtocol(Protocol):
        async def search(self, **kwargs: Any) -> SearchResultsIterable: ...
        async def close(self) -> None: ...
else:
    SearchClientProtocol = Any

__all__ = [
    "AzureAISearchTool",
    "BaseAzureAISearchTool",
    "SearchQuery",
    "SearchResults",
    "SearchResult",
    "VectorizableTextQuery",
    "VectorizedQuery",
    "VectorQuery",
]
logger = logging.getLogger(__name__)


class SearchQuery(BaseModel):
    """Search query parameters.

    This simplified interface only requires a search query string.
    All other parameters (top, filters, vector fields, etc.) are specified during tool creation
    rather than at query time, making it easier for language models to generate structured output.

    Args:
        query (str): The search query text.
    """

    query: str = Field(description="Search query text")


class SearchResult(BaseModel):
    """Search result.

    Args:
        score (float): The search score.
        content (ContentDict): The document content.
        metadata (MetadataDict): Additional metadata about the document.
    """

    score: float = Field(description="The search score")
    content: ContentDict = Field(description="The document content")
    metadata: MetadataDict = Field(description="Additional metadata about the document")


class SearchResults(BaseModel):
    """Container for search results.

    Args:
        results (List[SearchResult]): List of search results.
    """

    results: List[SearchResult] = Field(description="List of search results")


class EmbeddingProvider(Protocol):
    """Protocol defining the interface for embedding generation."""

    async def _get_embedding(self, query: str) -> List[float]:
        """Generate embedding vector for the query text."""
        ...


class EmbeddingProviderMixin:
    """Mixin class providing embedding generation functionality."""

    search_config: AzureAISearchConfig

    async def _get_embedding(self, query: str) -> List[float]:
        """Generate embedding vector for the query text."""
        if not hasattr(self, "search_config"):
            raise ValueError("Host class must have a search_config attribute")

        search_config = self.search_config
        embedding_provider = getattr(search_config, "embedding_provider", None)
        embedding_model = getattr(search_config, "embedding_model", None)

        if not embedding_provider or not embedding_model:
            raise ValueError(
                "Client-side embedding is not configured. `embedding_provider` and `embedding_model` must be set."
            ) from None

        if embedding_provider.lower() == "azure_openai":
            try:
                from openai import AsyncAzureOpenAI

                from azure.identity import DefaultAzureCredential
            except ImportError:
                raise ImportError(
                    "Azure OpenAI SDK is required for client-side embedding generation. "
                    "Please install it with: uv add openai azure-identity"
                ) from None

            api_key = getattr(search_config, "openai_api_key", None)
            api_version = getattr(search_config, "openai_api_version", "2023-11-01")
            endpoint = getattr(search_config, "openai_endpoint", None)

            if not endpoint:
                raise ValueError(
                    "Azure OpenAI endpoint (`openai_endpoint`) must be provided for client-side Azure OpenAI embeddings."
                ) from None

            if api_key:
                azure_client = AsyncAzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
            else:

                def get_token() -> str:
                    credential = DefaultAzureCredential()
                    token = credential.get_token("https://cognitiveservices.azure.com/.default")
                    if not token or not token.token:
                        raise ValueError("Failed to acquire token using DefaultAzureCredential for Azure OpenAI.")
                    return token.token

                azure_client = AsyncAzureOpenAI(
                    azure_ad_token_provider=get_token, api_version=api_version, azure_endpoint=endpoint
                )

            try:
                response = await azure_client.embeddings.create(model=embedding_model, input=query)
                return response.data[0].embedding
            except Exception as e:
                raise ValueError(f"Failed to generate embeddings with Azure OpenAI: {str(e)}") from e

        elif embedding_provider.lower() == "openai":
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError(
                    "OpenAI SDK is required for client-side embedding generation. "
                    "Please install it with: uv add openai"
                ) from None

            api_key = getattr(search_config, "openai_api_key", None)
            openai_client = AsyncOpenAI(api_key=api_key)

            try:
                response = await openai_client.embeddings.create(model=embedding_model, input=query)
                return response.data[0].embedding
            except Exception as e:
                raise ValueError(f"Failed to generate embeddings with OpenAI: {str(e)}") from e
        else:
            raise ValueError(
                f"Unsupported client-side embedding provider: {embedding_provider}. "
                "Currently supported providers are 'azure_openai' and 'openai'."
            )


class BaseAzureAISearchTool(
    BaseTool[SearchQuery, SearchResults], Component[AzureAISearchConfig], EmbeddingProvider, ABC
):
    """Abstract base class for Azure AI Search tools.

    This class defines the common interface and functionality for all Azure AI Search tools.
    It handles configuration management, client initialization, and the abstract methods
    that subclasses must implement.

    Attributes:
        search_config: Configuration parameters for the search service.

    Note:
        This is an abstract base class and should not be instantiated directly.
        Use concrete implementations or the factory methods in AzureAISearchTool.
    """

    component_config_schema = AzureAISearchConfig
    component_provider_override = "autogen_ext.tools.azure.BaseAzureAISearchTool"

    def __init__(
        self,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, AsyncTokenCredential, Dict[str, str]],
        description: Optional[str] = None,
        api_version: str = DEFAULT_API_VERSION,
        query_type: Literal["simple", "full", "semantic", "vector"] = "simple",
        search_fields: Optional[List[str]] = None,
        select_fields: Optional[List[str]] = None,
        vector_fields: Optional[List[str]] = None,
        top: Optional[int] = None,
        filter: Optional[str] = None,
        semantic_config_name: Optional[str] = None,
        enable_caching: bool = False,
        cache_ttl_seconds: int = 300,
        embedding_provider: Optional[str] = None,
        embedding_model: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_api_version: Optional[str] = None,
        openai_endpoint: Optional[str] = None,
    ):
        """Initialize the Azure AI Search tool.

        Args:
            name (str): The name of this tool instance
            endpoint (str): The full URL of your Azure AI Search service
            index_name (str): Name of the search index to query
            credential (Union[AzureKeyCredential, TokenCredential, Dict[str, str]]): Azure credential for authentication
            description (Optional[str]): Optional description explaining the tool's purpose
            api_version (Optional[str]): Azure AI Search API version to use
            query_type (Literal["simple", "full", "semantic", "vector"]): Type of search to perform
            search_fields (Optional[List[str]]): Fields to search within documents
            select_fields (Optional[List[str]]): Fields to return in search results
            vector_fields (Optional[List[str]]): Fields to use for vector search
            top (Optional[int]): Maximum number of results to return
            filter (Optional[str]): OData filter expression to refine search results
            semantic_config_name (Optional[str]): Semantic configuration name for enhanced results
            enable_caching (bool): Whether to cache search results
            cache_ttl_seconds (int): How long to cache results in seconds
            embedding_provider (Optional[str]): Name of embedding provider for client-side embeddings
            embedding_model (Optional[str]): Model name for client-side embeddings
            openai_api_key (Optional[str]): API key for OpenAI/Azure OpenAI embeddings
            openai_api_version (Optional[str]): API version for Azure OpenAI embeddings
            openai_endpoint (Optional[str]): Endpoint URL for Azure OpenAI embeddings
        """
        if not has_azure_search:
            raise ImportError(
                "Azure Search SDK is required but not installed. "
                "Please install it with: pip install azure-search-documents>=11.4.0"
            )

        if description is None:
            description = (
                f"Search for information in the {index_name} index using Azure AI Search. "
                f"Supports full-text search with optional filters and semantic capabilities."
            )

        super().__init__(
            args_type=SearchQuery,
            return_type=SearchResults,
            name=name,
            description=description,
        )

        processed_credential = self._process_credential(credential)

        self.search_config: AzureAISearchConfig = AzureAISearchConfig(
            name=name,
            description=description,
            endpoint=endpoint,
            index_name=index_name,
            credential=processed_credential,
            api_version=api_version,
            query_type=query_type,
            search_fields=search_fields,
            select_fields=select_fields,
            vector_fields=vector_fields,
            top=top,
            filter=filter,
            semantic_config_name=semantic_config_name,
            enable_caching=enable_caching,
            cache_ttl_seconds=cache_ttl_seconds,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            openai_api_key=openai_api_key,
            openai_api_version=openai_api_version,
            openai_endpoint=openai_endpoint,
        )

        self._endpoint = endpoint
        self._index_name = index_name
        self._credential = processed_credential
        self._api_version = api_version

        self._client: Optional[SearchClient] = None
        self._cache: Dict[str, Dict[str, Any]] = {}

        if self.search_config.api_version == "2023-11-01" and self.search_config.vector_fields:
            warning_message = (
                f"When explicitly setting api_version='{self.search_config.api_version}' for vector search: "
                f"If client-side embedding is NOT configured (e.g., `embedding_model` is not set), "
                f"this tool defaults to service-side vectorization (VectorizableTextQuery), which may fail or have limitations with this API version. "
                f"If client-side embedding IS configured, the tool will use VectorizedQuery, which is generally compatible. "
                f"For robust vector search, consider omitting api_version (recommended to use SDK default) or use a newer API version."
            )
            logger.warning(warning_message)

    async def close(self) -> None:
        """Explicitly close the Azure SearchClient if needed (for cleanup)."""
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                pass
            finally:
                self._client = None

    def _process_credential(
        self, credential: Union[AzureKeyCredential, AsyncTokenCredential, Dict[str, str]]
    ) -> Union[AzureKeyCredential, AsyncTokenCredential]:
        """Process credential to ensure it's the correct type for async SearchClient.

        Converts dictionary credentials with 'api_key' to AzureKeyCredential objects.

        Args:
            credential: The credential in either object or dictionary form

        Returns:
            A properly formatted credential object

        Raises:
            ValueError: If the credential dictionary doesn't contain an 'api_key'
            TypeError: If the credential is not of a supported type
        """
        if isinstance(credential, dict):
            if "api_key" in credential:
                return AzureKeyCredential(credential["api_key"])
            raise ValueError("If credential is a dict, it must contain an 'api_key' key")

        if isinstance(credential, (AzureKeyCredential, AsyncTokenCredential)):
            return credential

        raise TypeError("Credential must be AzureKeyCredential, AsyncTokenCredential, or a valid dict")

    async def _get_client(self) -> SearchClient:
        """Get the search client for the configured index.

        Returns:
            SearchClient: Initialized search client

        Raises:
            ValueError: If index doesn't exist or authentication fails
        """
        if self._client is not None:
            return self._client

        try:
            self._client = SearchClient(
                endpoint=self.search_config.endpoint,
                index_name=self.search_config.index_name,
                credential=self.search_config.credential,
                api_version=self.search_config.api_version,
            )
            return self._client
        except ResourceNotFoundError as e:
            raise ValueError(f"Index '{self.search_config.index_name}' not found in Azure AI Search service.") from e
        except HttpResponseError as e:
            if e.status_code == 401:
                raise ValueError("Authentication failed. Please check your credentials.") from e
            elif e.status_code == 403:
                raise ValueError("Permission denied to access this index.") from e
            else:
                raise ValueError(f"Error connecting to Azure AI Search: {str(e)}") from e
        except Exception as e:
            raise ValueError(f"Unexpected error initializing search client: {str(e)}") from e

    async def run(
        self, args: Union[str, Dict[str, Any], SearchQuery], cancellation_token: Optional[CancellationToken] = None
    ) -> SearchResults:
        """Execute a search against the Azure AI Search index.

        Args:
            args: Search query text or SearchQuery object
            cancellation_token: Optional token to cancel the operation

        Returns:
            SearchResults: Container with search results and metadata

        Raises:
            ValueError: If the search query is empty or invalid
            ValueError: If there is an authentication error or other search issue
            asyncio.CancelledError: If the operation is cancelled
        """
        if isinstance(args, str):
            if not args.strip():
                raise ValueError("Search query cannot be empty")
            search_query = SearchQuery(query=args)
        elif isinstance(args, dict) and "query" in args:
            search_query = SearchQuery(query=args["query"])
        elif isinstance(args, SearchQuery):
            search_query = args
        else:
            raise ValueError("Invalid search query format. Expected string, dict with 'query', or SearchQuery")

        if cancellation_token is not None and cancellation_token.is_cancelled():
            raise asyncio.CancelledError("Operation cancelled")

        cache_key = ""
        if self.search_config.enable_caching:
            cache_key_parts = [
                search_query.query,
                str(self.search_config.top),
                self.search_config.query_type,
                ",".join(sorted(self.search_config.search_fields or [])),
                ",".join(sorted(self.search_config.select_fields or [])),
                ",".join(sorted(self.search_config.vector_fields or [])),
                str(self.search_config.filter or ""),
                str(self.search_config.semantic_config_name or ""),
            ]
            cache_key = ":".join(filter(None, cache_key_parts))
            if cache_key in self._cache:
                cache_entry = self._cache[cache_key]
                cache_age = time.time() - cache_entry["timestamp"]
                if cache_age < self.search_config.cache_ttl_seconds:
                    logger.debug(f"Using cached results for query: {search_query.query}")
                    return SearchResults(
                        results=[
                            SearchResult(score=r.score, content=r.content, metadata=r.metadata)
                            for r in cache_entry["results"]
                        ]
                    )

        try:
            search_kwargs: Dict[str, Any] = {}

            if self.search_config.query_type != "vector":
                search_kwargs["search_text"] = search_query.query
                search_kwargs["query_type"] = self.search_config.query_type

                if self.search_config.search_fields:
                    search_kwargs["search_fields"] = self.search_config.search_fields  # type: ignore[assignment]

                if self.search_config.query_type == "semantic" and self.search_config.semantic_config_name:
                    search_kwargs["semantic_configuration_name"] = self.search_config.semantic_config_name

            if self.search_config.select_fields:
                search_kwargs["select"] = self.search_config.select_fields  # type: ignore[assignment]
            if self.search_config.filter:
                search_kwargs["filter"] = str(self.search_config.filter)
            if self.search_config.top is not None:
                search_kwargs["top"] = self.search_config.top  # type: ignore[assignment]

            if self.search_config.vector_fields and len(self.search_config.vector_fields) > 0:
                if not search_query.query:
                    raise ValueError("Query text cannot be empty for vector search operations")

                use_client_side_embeddings = bool(
                    self.search_config.embedding_model and self.search_config.embedding_provider
                )

                vector_queries: List[Union[VectorizedQuery, VectorizableTextQuery]] = []
                if use_client_side_embeddings:
                    from azure.search.documents.models import VectorizedQuery

                    embedding_vector: List[float] = await self._get_embedding(search_query.query)
                    for field_spec in self.search_config.vector_fields:
                        fields = field_spec if isinstance(field_spec, str) else ",".join(field_spec)
                        vector_queries.append(
                            VectorizedQuery(
                                vector=embedding_vector,
                                k_nearest_neighbors=self.search_config.top or 5,
                                fields=fields,
                                kind="vector",
                            )
                        )
                else:
                    from azure.search.documents.models import VectorizableTextQuery

                    for field in self.search_config.vector_fields:
                        fields = field if isinstance(field, str) else ",".join(field)
                        vector_queries.append(
                            VectorizableTextQuery(  # type: ignore
                                text=search_query.query,
                                k_nearest_neighbors=self.search_config.top or 5,
                                fields=fields,
                                kind="vectorizable",
                            )
                        )

                search_kwargs["vector_queries"] = vector_queries  # type: ignore[assignment]

            if cancellation_token is not None:
                dummy_task = asyncio.create_task(asyncio.sleep(60))
                cancellation_token.link_future(dummy_task)

                def is_cancelled() -> bool:
                    return cancellation_token.is_cancelled()
            else:

                def is_cancelled() -> bool:
                    return False

            client = await self._get_client()
            search_results: SearchResultsIterable = await client.search(**search_kwargs)  # type: ignore[arg-type]

            results: List[SearchResult] = []
            async for doc in search_results:
                if is_cancelled():
                    raise asyncio.CancelledError("Operation was cancelled")

                try:
                    metadata: Dict[str, Any] = {}
                    content: Dict[str, Any] = {}

                    for key, value in doc.items():
                        if isinstance(key, str) and key.startswith(("@", "_")):
                            metadata[key] = value
                        else:
                            content[str(key)] = value

                    score = float(metadata.get("@search.score", 0.0))
                    results.append(SearchResult(score=score, content=content, metadata=metadata))
                except Exception as e:
                    logger.warning(f"Error processing search document: {e}")
                    continue

            if self.search_config.enable_caching:
                self._cache[cache_key] = {"results": results, "timestamp": time.time()}

            return SearchResults(results=results)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            error_msg = str(e)
            if isinstance(e, HttpResponseError):
                if hasattr(e, "message") and e.message:
                    error_msg = e.message

            if "not found" in error_msg.lower():
                raise ValueError(f"Index '{self.search_config.index_name}' not found.") from e
            elif "unauthorized" in error_msg.lower() or "401" in error_msg:
                raise ValueError(f"Authentication failed: {error_msg}") from e
            else:
                raise ValueError(f"Error from Azure AI Search: {error_msg}") from e

    def _to_config(self) -> AzureAISearchConfig:
        """Convert the current instance to a configuration object."""
        return self.search_config

    @property
    def schema(self) -> ToolSchema:
        """Return the schema for the tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query text"}},
                "required": ["query"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def return_value_as_string(self, value: SearchResults) -> str:
        """Convert the search results to a string representation."""
        if not value.results:
            return "No results found."

        result_strings: List[str] = []
        for i, result in enumerate(value.results, 1):
            content_items = [f"{k}: {str(v) if v is not None else 'None'}" for k, v in result.content.items()]
            content_str = ", ".join(content_items)
            result_strings.append(f"Result {i} (Score: {result.score:.2f}): {content_str}")

        return "\n".join(result_strings)

    @classmethod
    def _validate_config(
        cls, config_dict: Dict[str, Any], search_type: Literal["full_text", "vector", "hybrid"]
    ) -> None:
        """Validate configuration for specific search types."""
        credential = config_dict.get("credential")
        if isinstance(credential, str):
            raise TypeError("Credential must be AzureKeyCredential, AsyncTokenCredential, or a valid dict")
        if isinstance(credential, dict) and "api_key" not in credential:
            raise ValueError("If credential is a dict, it must contain an 'api_key' key")

        try:
            _ = AzureAISearchConfig(**config_dict)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}") from e

        if search_type == "vector":
            vector_fields = config_dict.get("vector_fields")
            if not vector_fields or len(vector_fields) == 0:
                raise ValueError("vector_fields must contain at least one field name for vector search")

        elif search_type == "hybrid":
            vector_fields = config_dict.get("vector_fields")
            search_fields = config_dict.get("search_fields")

            if not vector_fields or len(vector_fields) == 0:
                raise ValueError("vector_fields must contain at least one field name for hybrid search")

            if not search_fields or len(search_fields) == 0:
                raise ValueError("search_fields must contain at least one field name for hybrid search")

    @classmethod
    @abstractmethod
    def _from_config(cls, config: AzureAISearchConfig) -> "BaseAzureAISearchTool":
        """Create a tool instance from a configuration object.

        This is an abstract method that must be implemented by subclasses.
        """
        if cls is BaseAzureAISearchTool:
            raise NotImplementedError(
                "BaseAzureAISearchTool is an abstract base class and cannot be instantiated directly. "
                "Use a concrete implementation like AzureAISearchTool."
            )
        raise NotImplementedError("Subclasses must implement _from_config")

    @abstractmethod
    async def _get_embedding(self, query: str) -> List[float]:
        """Generate embedding vector for the query text."""
        raise NotImplementedError("Subclasses must implement _get_embedding")


_allow_private_constructor = ContextVar("_allow_private_constructor", default=False)


class AzureAISearchTool(EmbeddingProviderMixin, BaseAzureAISearchTool):
    """Azure AI Search tool for querying Azure search indexes.

    This tool provides a simplified interface for querying Azure AI Search indexes using
    various search methods. It's recommended to use the factory methods to create
    instances tailored for specific search types:

    1.  **Full-Text Search**: For traditional keyword-based searches, Lucene queries, or
        semantically re-ranked results.
        - Use `AzureAISearchTool.create_full_text_search()`
        - Supports `query_type`: "simple" (keyword), "full" (Lucene), "semantic".

    2.  **Vector Search**: For pure similarity searches based on vector embeddings.
        - Use `AzureAISearchTool.create_vector_search()`

    3.  **Hybrid Search**: For combining vector search with full-text or semantic search
        to get the benefits of both.
        - Use `AzureAISearchTool.create_hybrid_search()`
        - The text component can be "simple", "full", or "semantic" via the `query_type` parameter.

    Each factory method configures the tool with appropriate defaults and validations
    for the chosen search strategy.

    .. warning::
        If you set `query_type="semantic"`, you must also provide a valid `semantic_config_name`.
        This configuration must be set up in your Azure AI Search index beforehand.
    """

    component_provider_override = "autogen_ext.tools.azure.AzureAISearchTool"

    @classmethod
    def _from_config(cls, config: AzureAISearchConfig) -> "AzureAISearchTool":
        """Create a tool instance from a configuration object.

        Args:
            config: The configuration object with tool settings

        Returns:
            AzureAISearchTool: An initialized tool instance
        """
        token = _allow_private_constructor.set(True)
        try:
            instance = cls(
                name=config.name,
                description=config.description or "",
                endpoint=config.endpoint,
                index_name=config.index_name,
                credential=config.credential,
                api_version=config.api_version,
                query_type=config.query_type,
                search_fields=config.search_fields,
                select_fields=config.select_fields,
                vector_fields=config.vector_fields,
                top=config.top,
                filter=config.filter,
                semantic_config_name=config.semantic_config_name,
                enable_caching=config.enable_caching,
                cache_ttl_seconds=config.cache_ttl_seconds,
                embedding_provider=config.embedding_provider,
                embedding_model=config.embedding_model,
                openai_api_key=config.openai_api_key,
                openai_api_version=config.openai_api_version,
                openai_endpoint=config.openai_endpoint,
            )
            return instance
        finally:
            _allow_private_constructor.reset(token)

    @classmethod
    def _create_from_params(
        cls, config_dict: Dict[str, Any], search_type: Literal["full_text", "vector", "hybrid"]
    ) -> "AzureAISearchTool":
        """Private helper to create an instance from parameters after validation.

        Args:
            config_dict: Dictionary with configuration parameters
            search_type: Type of search for validation

        Returns:
            Configured AzureAISearchTool instance
        """
        cls._validate_config(config_dict, search_type)

        token = _allow_private_constructor.set(True)
        try:
            return cls(**config_dict)
        finally:
            _allow_private_constructor.reset(token)

    @classmethod
    def create_full_text_search(
        cls,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, AsyncTokenCredential, Dict[str, str]],
        description: Optional[str] = None,
        api_version: Optional[str] = None,
        query_type: Literal["simple", "full", "semantic"] = "simple",
        search_fields: Optional[List[str]] = None,
        select_fields: Optional[List[str]] = None,
        top: Optional[int] = 5,
        filter: Optional[str] = None,
        semantic_config_name: Optional[str] = None,
        enable_caching: bool = False,
        cache_ttl_seconds: int = 300,
    ) -> "AzureAISearchTool":
        """Create a tool for traditional text-based searches.

        This factory method creates an AzureAISearchTool optimized for full-text search,
        supporting keyword matching, Lucene syntax, and semantic search capabilities.

        Args:
            name: The name of this tool instance
            endpoint: The full URL of your Azure AI Search service
            index_name: Name of the search index to query
            credential: Azure credential for authentication (API key or token)
            description: Optional description explaining the tool's purpose
            api_version: Azure AI Search API version to use
            query_type: Type of text search to perform:

                • **simple** : Basic keyword search that matches exact terms and their variations
                • **full**: Advanced search using Lucene query syntax for complex queries
                • **semantic**: AI-powered search that understands meaning and context, providing enhanced relevance ranking
            search_fields: Fields to search within documents
            select_fields: Fields to return in search results
            top: Maximum number of results to return (default: 5)
            filter: OData filter expression to refine search results
            semantic_config_name: Semantic configuration name (required for semantic query_type)
            enable_caching: Whether to cache search results
            cache_ttl_seconds: How long to cache results in seconds

        Returns:
            An initialized AzureAISearchTool for full-text search

        Example:
            .. code-block:: python

                from azure.core.credentials import AzureKeyCredential
                from autogen_ext.tools.azure import AzureAISearchTool

                # Basic keyword search
                tool = AzureAISearchTool.create_full_text_search(
                    name="doc-search",
                    endpoint="https://your-search.search.windows.net",  # Your Azure AI Search endpoint
                    index_name="<your-index>",  # Name of your search index
                    credential=AzureKeyCredential("<your-key>"),  # Your Azure AI Search admin key
                    query_type="simple",  # Enable keyword search
                    search_fields=["content", "title"],  # Required: fields to search within
                    select_fields=["content", "title", "url"],  # Optional: fields to return
                    top=5,
                )

                # full text (Lucene query) search
                full_text_tool = AzureAISearchTool.create_full_text_search(
                    name="doc-search",
                    endpoint="https://your-search.search.windows.net",  # Your Azure AI Search endpoint
                    index_name="<your-index>",  # Name of your search index
                    credential=AzureKeyCredential("<your-key>"),  # Your Azure AI Search admin key
                    query_type="full",  # Enable Lucene query syntax
                    search_fields=["content", "title"],  # Required: fields to search within
                    select_fields=["content", "title", "url"],  # Optional: fields to return
                    top=5,
                )

                # Semantic search with re-ranking
                # Note: Make sure your index has semantic configuration enabled
                semantic_tool = AzureAISearchTool.create_full_text_search(
                    name="semantic-search",
                    endpoint="https://your-search.search.windows.net",
                    index_name="<your-index>",
                    credential=AzureKeyCredential("<your-key>"),
                    query_type="semantic",  # Enable semantic ranking
                    semantic_config_name="<your-semantic-config>",  # Required for semantic search
                    search_fields=["content", "title"],  # Required: fields to search within
                    select_fields=["content", "title", "url"],  # Optional: fields to return
                    top=5,
                )

                # The search tool can be used with an Agent
                # assistant = Agent("assistant", tools=[semantic_tool])
        """
        if query_type == "semantic" and not semantic_config_name:
            raise ValueError("semantic_config_name is required when query_type is 'semantic'")

        config_dict = {
            "name": name,
            "endpoint": endpoint,
            "index_name": index_name,
            "credential": credential,
            "description": description,
            "api_version": api_version or DEFAULT_API_VERSION,
            "query_type": query_type,
            "search_fields": search_fields,
            "select_fields": select_fields,
            "top": top,
            "filter": filter,
            "semantic_config_name": semantic_config_name,
            "enable_caching": enable_caching,
            "cache_ttl_seconds": cache_ttl_seconds,
        }

        return cls._create_from_params(config_dict, "full_text")

    @classmethod
    def create_vector_search(
        cls,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, AsyncTokenCredential, Dict[str, str]],
        vector_fields: List[str],
        description: Optional[str] = None,
        api_version: Optional[str] = None,
        select_fields: Optional[List[str]] = None,
        top: int = 5,
        filter: Optional[str] = None,
        enable_caching: bool = False,
        cache_ttl_seconds: int = 300,
        embedding_provider: Optional[str] = None,
        embedding_model: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_api_version: Optional[str] = None,
        openai_endpoint: Optional[str] = None,
    ) -> "AzureAISearchTool":
        """Create a tool for pure vector/similarity search.

        This factory method creates an AzureAISearchTool optimized for vector search,
        allowing for semantic similarity-based matching using vector embeddings.

        Args:
            name: The name of this tool instance
            endpoint: The full URL of your Azure AI Search service
            index_name: Name of the search index to query
            credential: Azure credential for authentication (API key or token)
            vector_fields: Fields to use for vector search (required)
            description: Optional description explaining the tool's purpose
            api_version: Azure AI Search API version to use
            select_fields: Fields to return in search results
            top: Maximum number of results to return / k in k-NN (default: 5)
            filter: OData filter expression to refine search results
            enable_caching: Whether to cache search results
            cache_ttl_seconds: How long to cache results in seconds
            embedding_provider: Provider for client-side embeddings (e.g., 'azure_openai', 'openai')
            embedding_model: Model for client-side embeddings (e.g., 'text-embedding-ada-002')
            openai_api_key: API key for OpenAI/Azure OpenAI embeddings
            openai_api_version: API version for Azure OpenAI embeddings
            openai_endpoint: Endpoint URL for Azure OpenAI embeddings

        Returns:
            An initialized AzureAISearchTool for vector search

        Raises:
            ValueError: If vector_fields is empty
            ValueError: If embedding_provider is 'azure_openai' without openai_endpoint
            ValueError: If required parameters are missing or invalid

        Example Usage:
            .. code-block:: python

                from azure.core.credentials import AzureKeyCredential
                from autogen_ext.tools.azure import AzureAISearchTool

                # Vector search with service-side vectorization
                tool = AzureAISearchTool.create_vector_search(
                    name="vector-search",
                    endpoint="https://your-search.search.windows.net",  # Your Azure AI Search endpoint
                    index_name="<your-index>",  # Name of your search index
                    credential=AzureKeyCredential("<your-key>"),  # Your Azure AI Search admin key
                    vector_fields=["content_vector"],  # Your vector field name
                    select_fields=["content", "title", "url"],  # Fields to return in results
                    top=5,
                )

                # Vector search with Azure OpenAI embeddings
                azure_openai_tool = AzureAISearchTool.create_vector_search(
                    name="azure-openai-vector-search",
                    endpoint="https://your-search.search.windows.net",
                    index_name="<your-index>",
                    credential=AzureKeyCredential("<your-key>"),
                    vector_fields=["content_vector"],
                    embedding_provider="azure_openai",  # Use Azure OpenAI for embeddings
                    embedding_model="text-embedding-ada-002",  # Embedding model to use
                    openai_endpoint="https://your-openai.openai.azure.com",  # Your Azure OpenAI endpoint
                    openai_api_key="<your-openai-key>",  # Your Azure OpenAI key
                    openai_api_version="2024-02-15-preview",  # Azure OpenAI API version
                    select_fields=["content", "title", "url"],  # Fields to return in results
                    top=5,
                )

                # Vector search with OpenAI embeddings
                openai_tool = AzureAISearchTool.create_vector_search(
                    name="openai-vector-search",
                    endpoint="https://your-search.search.windows.net",
                    index_name="<your-index>",
                    credential=AzureKeyCredential("<your-key>"),
                    vector_fields=["content_vector"],
                    embedding_provider="openai",  # Use OpenAI for embeddings
                    embedding_model="text-embedding-ada-002",  # Embedding model to use
                    openai_api_key="<your-openai-key>",  # Your OpenAI API key
                    select_fields=["content", "title", "url"],  # Fields to return in results
                    top=5,
                )

                # Use the tool with an Agent
                # assistant = Agent("assistant", tools=[azure_openai_tool])
        """
        if embedding_provider == "azure_openai" and not openai_endpoint:
            raise ValueError("openai_endpoint is required when embedding_provider is 'azure_openai'")

        config_dict = {
            "name": name,
            "endpoint": endpoint,
            "index_name": index_name,
            "credential": credential,
            "description": description,
            "api_version": api_version or DEFAULT_API_VERSION,
            "query_type": "vector",
            "select_fields": select_fields,
            "vector_fields": vector_fields,
            "top": top,
            "filter": filter,
            "enable_caching": enable_caching,
            "cache_ttl_seconds": cache_ttl_seconds,
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_model,
            "openai_api_key": openai_api_key,
            "openai_api_version": openai_api_version,
            "openai_endpoint": openai_endpoint,
        }

        return cls._create_from_params(config_dict, "vector")

    @classmethod
    def create_hybrid_search(
        cls,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, AsyncTokenCredential, Dict[str, str]],
        vector_fields: List[str],
        search_fields: List[str],
        description: Optional[str] = None,
        api_version: Optional[str] = None,
        query_type: Literal["simple", "full", "semantic"] = "simple",
        select_fields: Optional[List[str]] = None,
        top: int = 5,
        filter: Optional[str] = None,
        semantic_config_name: Optional[str] = None,
        enable_caching: bool = False,
        cache_ttl_seconds: int = 300,
        embedding_provider: Optional[str] = None,
        embedding_model: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_api_version: Optional[str] = None,
        openai_endpoint: Optional[str] = None,
    ) -> "AzureAISearchTool":
        """Create a tool that combines vector and text search capabilities.

        This factory method creates an AzureAISearchTool configured for hybrid search,
        which combines the benefits of vector similarity and traditional text search.

        Args:
            name: The name of this tool instance
            endpoint: The full URL of your Azure AI Search service
            index_name: Name of the search index to query
            credential: Azure credential for authentication (API key or token)
            vector_fields: Fields to use for vector search (required)
            search_fields: Fields to use for text search (required)
            description: Optional description explaining the tool's purpose
            api_version: Azure AI Search API version to use
            query_type: Type of text search to perform:

                • **simple**: Basic keyword search that matches exact terms and their variations
                • **full**: Advanced search using Lucene query syntax for complex queries
                • **semantic**: AI-powered search that understands meaning and context, providing enhanced relevance ranking
            select_fields: Fields to return in search results
            top: Maximum number of results to return (default: 5)
            filter: OData filter expression to refine search results
            semantic_config_name: Semantic configuration name (required if query_type="semantic")
            enable_caching: Whether to cache search results
            cache_ttl_seconds: How long to cache results in seconds
            embedding_provider: Provider for client-side embeddings (e.g., 'azure_openai', 'openai')
            embedding_model: Model for client-side embeddings (e.g., 'text-embedding-ada-002')
            openai_api_key: API key for OpenAI/Azure OpenAI embeddings
            openai_api_version: API version for Azure OpenAI embeddings
            openai_endpoint: Endpoint URL for Azure OpenAI embeddings

        Returns:
            An initialized AzureAISearchTool for hybrid search

        Raises:
            ValueError: If vector_fields or search_fields is empty
            ValueError: If query_type is "semantic" without semantic_config_name
            ValueError: If embedding_provider is 'azure_openai' without openai_endpoint
            ValueError: If required parameters are missing or invalid

        Example:
            .. code-block:: python

                from azure.core.credentials import AzureKeyCredential
                from autogen_ext.tools.azure import AzureAISearchTool

                # Basic hybrid search with service-side vectorization
                tool = AzureAISearchTool.create_hybrid_search(
                    name="hybrid-search",
                    endpoint="https://your-search.search.windows.net",  # Your Azure AI Search endpoint
                    index_name="<your-index>",  # Name of your search index
                    credential=AzureKeyCredential("<your-key>"),  # Your Azure AI Search admin key
                    vector_fields=["content_vector"],  # Your vector field name
                    search_fields=["content", "title"],  # Your searchable fields
                    top=5,
                )

                # Hybrid search with semantic ranking and Azure OpenAI embeddings
                semantic_tool = AzureAISearchTool.create_hybrid_search(
                    name="semantic-hybrid-search",
                    endpoint="https://your-search.search.windows.net",
                    index_name="<your-index>",
                    credential=AzureKeyCredential("<your-key>"),
                    vector_fields=["content_vector"],
                    search_fields=["content", "title"],
                    query_type="semantic",  # Enable semantic ranking
                    semantic_config_name="<your-semantic-config>",  # Your semantic config name
                    embedding_provider="azure_openai",  # Use Azure OpenAI for embeddings
                    embedding_model="text-embedding-ada-002",  # Embedding model to use
                    openai_endpoint="https://your-openai.openai.azure.com",  # Your Azure OpenAI endpoint
                    openai_api_key="<your-openai-key>",  # Your Azure OpenAI key
                    openai_api_version="2024-02-15-preview",  # Azure OpenAI API version
                    select_fields=["content", "title", "url"],  # Fields to return in results
                    filter="language eq 'en'",  # Optional OData filter
                    top=5,
                )

                # The search tool can be used with an Agent
                # assistant = Agent("assistant", tools=[semantic_tool])
        """
        if query_type == "semantic" and not semantic_config_name:
            raise ValueError("semantic_config_name is required when query_type is 'semantic'")

        if embedding_provider == "azure_openai" and not openai_endpoint:
            raise ValueError("openai_endpoint is required when embedding_provider is 'azure_openai'")

        config_dict = {
            "name": name,
            "endpoint": endpoint,
            "index_name": index_name,
            "credential": credential,
            "description": description,
            "api_version": api_version or DEFAULT_API_VERSION,
            "query_type": query_type,
            "search_fields": search_fields,
            "select_fields": select_fields,
            "vector_fields": vector_fields,
            "top": top,
            "filter": filter,
            "semantic_config_name": semantic_config_name,
            "enable_caching": enable_caching,
            "cache_ttl_seconds": cache_ttl_seconds,
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_model,
            "openai_api_key": openai_api_key,
            "openai_api_version": openai_api_version,
            "openai_endpoint": openai_endpoint,
        }

        return cls._create_from_params(config_dict, "hybrid")
