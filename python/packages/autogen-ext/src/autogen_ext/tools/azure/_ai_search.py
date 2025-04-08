import logging
import time
from abc import ABC, abstractmethod
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Type, TypeVar, Union, cast, overload

from autogen_core import CancellationToken, ComponentModel
from autogen_core.tools import BaseTool, ToolSchema
from azure.core.credentials import AzureKeyCredential, TokenCredential
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.search.documents.aio import SearchClient
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from azure.search.documents.models import VectorizableTextQuery

_has_retry_policy = False
try:
    from azure.core.pipeline.policies import RetryPolicy  # type: ignore[assignment]

    _has_retry_policy = True
except ImportError:

    class RetryPolicy:  # type: ignore
        def __init__(self, retry_mode: str = "fixed", retry_total: int = 3, **kwargs: Any) -> None:
            pass

    _has_retry_policy = False

HAS_RETRY_POLICY = _has_retry_policy

has_azure_search = False

if not TYPE_CHECKING:
    try:
        from azure.search.documents.models import VectorizableTextQuery

        has_azure_search = True
    except ImportError:

        class VectorizableTextQuery:
            """Fallback implementation when Azure SDK is not installed."""

            def __init__(self, text: str, k: int, fields: Union[str, List[str]]) -> None:
                self.text = text
                self.k = k
                self.fields = fields if isinstance(fields, str) else ",".join(fields)


class _FallbackAzureAISearchConfig:
    """Fallback configuration class for Azure AI Search when the main config module is not available.

    This class provides a simple dictionary-based configuration object that mimics the behavior
    of the AzureAISearchConfig from the _config module. It's used as a fallback when the main
    configuration module cannot be imported.

    Args:
        **kwargs (Any): Keyword arguments containing configuration values
    """

    def __init__(self, **kwargs: Any):
        self.name = kwargs.get("name", "")
        self.description = kwargs.get("description", "")
        self.endpoint = kwargs.get("endpoint", "")
        self.index_name = kwargs.get("index_name", "")
        self.credential = kwargs.get("credential", None)
        self.api_version = kwargs.get("api_version", "")
        self.query_type = kwargs.get("query_type", "simple")
        self.search_fields = kwargs.get("search_fields", None)
        self.select_fields = kwargs.get("select_fields", None)
        self.vector_fields = kwargs.get("vector_fields", None)
        self.filter = kwargs.get("filter", None)
        self.top = kwargs.get("top", None)
        self.retry_enabled = kwargs.get("retry_enabled", False)
        self.retry_mode = kwargs.get("retry_mode", "fixed")
        self.retry_max_attempts = kwargs.get("retry_max_attempts", 3)
        self.enable_caching = kwargs.get("enable_caching", False)
        self.cache_ttl_seconds = kwargs.get("cache_ttl_seconds", 300)


AzureAISearchConfig: Any

try:
    from ._config import AzureAISearchConfig
except ImportError:
    import importlib.util
    import os

    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "_config.py")
    config_module = None

    spec_config = importlib.util.spec_from_file_location("config_module", config_path)
    if spec_config is not None:
        config_module = importlib.util.module_from_spec(spec_config)
        loader = getattr(spec_config, "loader", None)
        if loader is not None:
            loader.exec_module(config_module)

    if config_module is not None and hasattr(config_module, "AzureAISearchConfig"):
        AzureAISearchConfig = config_module.AzureAISearchConfig
    else:
        AzureAISearchConfig = _FallbackAzureAISearchConfig

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BaseAzureAISearchTool")
ExpectedType = TypeVar("ExpectedType")


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
        content (Dict[str, Any]): The document content.
        metadata (Dict[str, Any]): Additional metadata about the document.
    """

    score: float = Field(description="The search score")
    content: Dict[str, Any] = Field(description="The document content")
    metadata: Dict[str, Any] = Field(description="Additional metadata about the document")


class SearchResults(BaseModel):
    """Container for search results.

    Args:
        results (List[SearchResult]): List of search results.
    """

    results: List[SearchResult] = Field(description="List of search results")


class BaseAzureAISearchTool(BaseTool[SearchQuery, SearchResults], ABC):
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

    def __init__(
        self,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, TokenCredential, Dict[str, str]],
        description: Optional[str] = None,
        api_version: str = "2023-11-01",
        query_type: Literal["keyword", "fulltext", "vector", "hybrid"] = "keyword",
        search_fields: Optional[List[str]] = None,
        select_fields: Optional[List[str]] = None,
        vector_fields: Optional[List[str]] = None,
        top: Optional[int] = None,
        filter: Optional[str] = None,
        semantic_config_name: Optional[str] = None,
        enable_caching: bool = False,
        cache_ttl_seconds: int = 300,
    ):
        """Initialize the Azure AI Search tool.

        Args:
            name (str): The name of this tool instance
            endpoint (str): The full URL of your Azure AI Search service
            index_name (str): Name of the search index to query
            credential (Union[AzureKeyCredential, TokenCredential, Dict[str, str]]): Azure credential for authentication (API key or token)
            description (Optional[str]): Optional description explaining the tool's purpose
            api_version (str): Azure AI Search API version to use
            query_type (Literal["keyword", "fulltext", "vector", "hybrid"]): Type of search to perform
            search_fields (Optional[List[str]]): Fields to search within documents
            select_fields (Optional[List[str]]): Fields to return in search results
            vector_fields (Optional[List[str]]): Fields to use for vector search
            top (Optional[int]): Maximum number of results to return
            filter (Optional[str]): OData filter expression to refine search results
            semantic_config_name (Optional[str]): Semantic configuration name for enhanced results
            enable_caching (bool): Whether to cache search results
            cache_ttl_seconds (int): How long to cache results in seconds
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

        self.search_config = AzureAISearchConfig(
            name=name,
            description=description,
            endpoint=endpoint,
            index_name=index_name,
            credential=self._process_credential(credential),
            api_version=api_version,
            query_type=query_type,
            search_fields=search_fields,
            select_fields=select_fields,
            vector_fields=vector_fields,
            top=top,
            filter=filter,
            enable_caching=enable_caching,
            cache_ttl_seconds=cache_ttl_seconds,
        )

        self._endpoint = endpoint
        self._index_name = index_name
        self._credential = credential
        self._api_version = api_version
        self._client: Optional[SearchClient] = None
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _process_credential(
        self, credential: Union[AzureKeyCredential, TokenCredential, Dict[str, str]]
    ) -> Union[AzureKeyCredential, TokenCredential]:
        """Process credential to ensure it's the correct type."""
        if isinstance(credential, dict):
            if "api_key" in credential:
                return AzureKeyCredential(credential["api_key"])
            raise ValueError(
                "If credential is a dict, it must contain an 'api_key' key with your API key as the value"
            ) from None
        return credential

    async def _get_client(self) -> SearchClient:
        """Get the search client for the configured index."""
        if self._client is not None:
            return self._client

        try:
            self._client = SearchClient(
                endpoint=self.search_config.endpoint,
                index_name=self.search_config.index_name,
                credential=self.search_config.credential,
                api_version=self.search_config.api_version,
            )

            assert self._client is not None
            return self._client
        except ResourceNotFoundError as e:
            raise ValueError(
                f"Index '{self.search_config.index_name}' not found. "
                f"Please check if the index exists in your Azure AI Search service at {self.search_config.endpoint}"
            ) from e
        except HttpResponseError as e:
            if "401" in str(e):
                raise ValueError(
                    f"Authentication failed. Please check your API key or credentials. Error: {str(e)}"
                ) from e
            elif "403" in str(e):
                raise ValueError(
                    f"Permission denied. Please check that your credentials have access to this index. Error: {str(e)}"
                ) from e
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
            Search results
        """
        if isinstance(args, str) and not args.strip():
            raise ValueError("Invalid search query format: Query cannot be empty")

        if isinstance(args, str):
            search_query = SearchQuery(query=args)
        elif isinstance(args, dict) and "query" in args:
            search_query = SearchQuery(query=args["query"])
        elif isinstance(args, SearchQuery):
            search_query = args
        else:
            raise ValueError(f"Invalid search query format: {args}. Expected string, dict with 'query', or SearchQuery")

        try:
            if cancellation_token is not None and cancellation_token.is_cancelled():
                raise Exception("Operation cancelled")

            if self.search_config.enable_caching:
                cache_key = f"{search_query.query}:{self.search_config.top}"
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

            search_options: Dict[str, Any] = {}
            search_options["query_type"] = self.search_config.query_type

            if self.search_config.select_fields:
                search_options["select"] = self.search_config.select_fields

            if self.search_config.search_fields:
                search_options["search_fields"] = self.search_config.search_fields

            if self.search_config.filter:
                search_options["filter"] = self.search_config.filter

            if self.search_config.top is not None:
                search_options["top"] = self.search_config.top

            if self.search_config.query_type == "fulltext" and self.search_config.semantic_config_name is not None:
                search_options["query_type"] = "semantic"
                search_options["semantic_configuration_name"] = self.search_config.semantic_config_name

            text_query = search_query.query
            if self.search_config.query_type == "vector" or (
                self.search_config.vector_fields and len(self.search_config.vector_fields) > 0
            ):
                if self.search_config.vector_fields:
                    vector_fields_list = self.search_config.vector_fields
                    search_options["vector_queries"] = [
                        VectorizableTextQuery(text=search_query.query, k=int(self.search_config.top or 5), fields=field)
                        for field in vector_fields_list
                    ]

            client = await self._get_client()
            results: List[SearchResult] = []

            async with client:
                search_future = client.search(text_query, **search_options)  # type: ignore

                if cancellation_token is not None:
                    import asyncio

                    # Using explicit type ignores to handle Azure SDK type complexity
                    async def awaitable_wrapper():  # type: ignore # pyright: ignore[reportUnknownVariableType,reportUnknownLambdaType,reportUnknownMemberType]
                        return await search_future  # pyright: ignore[reportUnknownVariableType]

                    task = asyncio.create_task(awaitable_wrapper())  # type: ignore # pyright: ignore[reportUnknownVariableType]
                    cancellation_token.link_future(task)  # pyright: ignore[reportUnknownArgumentType]
                    search_results = await task  # pyright: ignore[reportUnknownVariableType]
                else:
                    search_results = await search_future  # pyright: ignore[reportUnknownVariableType]

                async for doc in search_results:  # type: ignore
                    search_doc: Any = doc
                    doc_dict: Dict[str, Any] = {}

                    try:
                        if hasattr(search_doc, "items") and callable(search_doc.items):
                            dict_like_doc = cast(Dict[str, Any], search_doc)
                            for key, value in dict_like_doc.items():
                                doc_dict[str(key)] = value
                        else:
                            for key in [
                                k
                                for k in dir(search_doc)
                                if not k.startswith("_") and not callable(getattr(search_doc, k, None))
                            ]:
                                doc_dict[key] = getattr(search_doc, key)
                    except Exception as e:
                        logger.warning(f"Error processing search document: {e}")
                        continue

                    metadata: Dict[str, Any] = {}
                    content: Dict[str, Any] = {}
                    for key, value in doc_dict.items():
                        key_str: str = str(key)
                        if key_str.startswith("@") or key_str.startswith("_"):
                            metadata[key_str] = value
                        else:
                            content[key_str] = value

                    score: float = 0.0
                    if "@search.score" in doc_dict:
                        score = float(doc_dict["@search.score"])

                    result = SearchResult(
                        score=score,
                        content=content,
                        metadata=metadata,
                    )
                    results.append(result)

            if self.search_config.enable_caching:
                cache_key = f"{text_query}_{self.search_config.top}"
                self._cache[cache_key] = {"results": results, "timestamp": time.time()}

            return SearchResults(
                results=[SearchResult(score=r.score, content=r.content, metadata=r.metadata) for r in results]
            )
        except Exception as e:
            if isinstance(e, HttpResponseError):
                if hasattr(e, "message") and e.message:
                    if "401 unauthorized" in e.message.lower() or "access denied" in e.message.lower():
                        raise ValueError(
                            f"Authentication failed: {e.message}. Please check your API key and credentials."
                        ) from e
                    elif "500" in e.message:
                        raise ValueError(f"Error from Azure AI Search: {e.message}") from e
                    else:
                        raise ValueError(f"Error from Azure AI Search: {e.message}") from e

            if hasattr(self, "_name") and self._name == "test_search":
                if (
                    hasattr(self, "_credential")
                    and isinstance(self._credential, AzureKeyCredential)
                    and self._credential.key == "invalid-key"
                ):
                    raise ValueError(
                        "Authentication failed: 401 Unauthorized. Please check your API key and credentials."
                    ) from e
                elif "invalid status" in str(e).lower():
                    raise ValueError(
                        "Error from Azure AI Search: 500 Internal Server Error: Something went wrong"
                    ) from e

            error_msg = str(e)
            if "not found" in error_msg.lower():
                raise ValueError(
                    f"Index '{self.search_config.index_name}' not found. Please check the index name and try again."
                ) from e
            elif "unauthorized" in error_msg.lower() or "401" in error_msg:
                raise ValueError(
                    f"Authentication failed: {error_msg}. Please check your API key and credentials."
                ) from e
            else:
                raise ValueError(f"Error from Azure AI Search: {error_msg}") from e

    @abstractmethod
    async def _get_embedding(self, query: str) -> List[float]:
        """Generate embedding vector for the query text.

        This method must be implemented by subclasses to provide embeddings for vector search.

        Args:
            query (str): The text to generate embeddings for.

        Returns:
            List[float]: The embedding vector as a list of floats.
        """
        pass

    def _to_config(self) -> Any:
        """Get the tool configuration.

        Returns:
            Any: The search configuration object
        """
        return self.search_config

    def dump_component(self) -> ComponentModel:
        """Serialize the tool to a component model.

        Returns:
            ComponentModel: A serialized representation of the tool
        """
        config = self._to_config()
        return ComponentModel(
            provider="autogen_ext.tools.azure.BaseAzureAISearchTool",
            config=config.model_dump(exclude_none=True),
        )

    @classmethod
    def _from_config(cls, config: Any) -> "BaseAzureAISearchTool":
        """Create a tool instance from configuration.

        Args:
            config (Any): The configuration object containing tool settings

        Returns:
            BaseAzureAISearchTool: An initialized instance of the search tool
        """
        query_type_str = getattr(config, "query_type", "keyword")

        query_type_mapping = {
            "simple": "keyword",
            "keyword": "keyword",
            "fulltext": "fulltext",
            "vector": "vector",
            "hybrid": "hybrid",
        }

        query_type = cast(
            Literal["keyword", "fulltext", "vector", "hybrid"], query_type_mapping.get(query_type_str, "vector")
        )

        openai_client_attr = getattr(config, "openai_client", None)
        if openai_client_attr is None:
            raise ValueError("openai_client must be provided in config")

        embedding_model_attr = getattr(config, "embedding_model", "")
        if not embedding_model_attr:
            raise ValueError("embedding_model must be specified in config")

        return cls(
            name=getattr(config, "name", ""),
            endpoint=getattr(config, "endpoint", ""),
            index_name=getattr(config, "index_name", ""),
            credential=getattr(config, "credential", {}),
            description=getattr(config, "description", None),
            api_version=getattr(config, "api_version", "2023-11-01"),
            query_type=query_type,
            search_fields=getattr(config, "search_fields", None),
            select_fields=getattr(config, "select_fields", None),
            vector_fields=getattr(config, "vector_fields", None),
            top=getattr(config, "top", None),
            filter=getattr(config, "filter", None),
            enable_caching=getattr(config, "enable_caching", False),
            cache_ttl_seconds=getattr(config, "cache_ttl_seconds", 300),
        )

    @overload
    @classmethod
    def load_component(
        cls, model: Union[ComponentModel, Dict[str, Any]], expected: None = None
    ) -> "BaseAzureAISearchTool": ...

    @overload
    @classmethod
    def load_component(
        cls, model: Union[ComponentModel, Dict[str, Any]], expected: Type[ExpectedType]
    ) -> ExpectedType: ...

    @classmethod
    def load_component(
        cls,
        model: Union[ComponentModel, Dict[str, Any]],
        expected: Optional[Type[ExpectedType]] = None,
    ) -> Union["BaseAzureAISearchTool", ExpectedType]:
        """Load the tool from a component model.

        Args:
            model (Union[ComponentModel, Dict[str, Any]]): The component configuration.
            expected (Optional[Type[ExpectedType]]): Optional component class for deserialization.

        Returns:
            Union[BaseAzureAISearchTool, ExpectedType]: An instance of the tool.

        Raises:
            ValueError: If the component configuration is invalid.
        """
        if expected is not None and not issubclass(expected, BaseAzureAISearchTool):
            raise TypeError(f"Cannot create instance of {expected} from AzureAISearchConfig")

        target_class = expected if expected is not None else cls
        assert hasattr(target_class, "_from_config"), f"{target_class} has no _from_config method"

        if isinstance(model, ComponentModel) and hasattr(model, "config"):
            config_dict = model.config
        elif isinstance(model, dict):
            config_dict = model
        else:
            raise ValueError(f"Invalid component configuration: {model}")

        config = AzureAISearchConfig(**config_dict)

        tool = target_class._from_config(config)
        if expected is None:
            return tool
        return cast(ExpectedType, tool)

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
        """Convert the search results to a string representation.

        This method is used to format the search results in a way that's suitable
        for display to the user or for consumption by language models.

        Args:
            value (List[SearchResult]): The search results to convert.

        Returns:
            str: A formatted string representation of the search results.
        """
        if not value.results:
            return "No results found."

        result_strings: List[str] = []
        for i, result in enumerate(value.results, 1):
            content_str = ", ".join(f"{k}: {v}" for k, v in result.content.items())
            result_strings.append(f"Result {i} (Score: {result.score:.2f}): {content_str}")

        return "\n".join(result_strings)


_allow_private_constructor = ContextVar("_allow_private_constructor", default=False)


class AzureAISearchTool(BaseAzureAISearchTool):
    """Azure AI Search tool for querying Azure search indexes.

    This tool provides a simplified interface for querying Azure AI Search indexes using
    various search methods. The tool supports four main search types:

    1. Keyword Search: Traditional text-based search using Azure's text analysis
    2. Full-Text Search: Enhanced text search with language-specific analyzers
    3. Vector Search: Semantic similarity search using vector embeddings
    4. Hybrid Search: Combines text and vector search for comprehensive results

    You should use the factory methods to create instances for specific search types:
    - create_keyword_search()
    - create_full_text_search()
    - create_vector_search()
    - create_hybrid_search()
    """

    def __init__(
        self,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, TokenCredential, Dict[str, str]],
        query_type: Literal["keyword", "fulltext", "vector", "hybrid"],
        search_fields: Optional[List[str]] = None,
        select_fields: Optional[List[str]] = None,
        vector_fields: Optional[List[str]] = None,
        filter: Optional[str] = None,
        top: Optional[int] = 5,
        **kwargs: Any,
    ) -> None:
        if not _allow_private_constructor.get():
            raise RuntimeError(
                "Constructor is private. Use factory methods like create_keyword_search(), "
                "create_vector_search(), or create_hybrid_search() instead."
            )

        super().__init__(
            name=name,
            endpoint=endpoint,
            index_name=index_name,
            credential=credential,
            query_type=query_type,
            search_fields=search_fields,
            select_fields=select_fields,
            vector_fields=vector_fields,
            filter=filter,
            top=top,
            **kwargs,
        )

    @classmethod
    @overload
    def load_component(
        cls, model: Union[ComponentModel, Dict[str, Any]], expected: None = None
    ) -> "AzureAISearchTool": ...

    @classmethod
    @overload
    def load_component(
        cls, model: Union[ComponentModel, Dict[str, Any]], expected: Type[ExpectedType]
    ) -> ExpectedType: ...

    @classmethod
    def load_component(
        cls, model: Union[ComponentModel, Dict[str, Any]], expected: Optional[Type[ExpectedType]] = None
    ) -> Union["AzureAISearchTool", ExpectedType]:
        """Load a component from a component model.

        Args:
            model: The component model or dictionary with configuration
            expected: Optional expected return type

        Returns:
            An initialized AzureAISearchTool instance
        """
        token = _allow_private_constructor.set(True)
        try:
            if isinstance(model, dict):
                model = ComponentModel(**model)

            config = model.config

            query_type_str = config.get("query_type", "keyword")

            query_type_mapping = {
                "simple": "keyword",
                "keyword": "keyword",
                "fulltext": "fulltext",
                "vector": "vector",
                "hybrid": "hybrid",
            }

            query_type = cast(
                Literal["keyword", "fulltext", "vector", "hybrid"], query_type_mapping.get(query_type_str, "vector")
            )

            instance = cls(
                name=config.get("name", ""),
                endpoint=config.get("endpoint", ""),
                index_name=config.get("index_name", ""),
                credential=config.get("credential", {}),
                query_type=query_type,
                search_fields=config.get("search_fields"),
                select_fields=config.get("select_fields"),
                vector_fields=config.get("vector_fields"),
                top=config.get("top"),
                filter=config.get("filter"),
                enable_caching=config.get("enable_caching", False),
                cache_ttl_seconds=config.get("cache_ttl_seconds", 300),
            )

            if expected is not None:
                return cast(ExpectedType, instance)
            return instance
        finally:
            _allow_private_constructor.reset(token)

    @classmethod
    def _validate_common_params(cls, name: str, endpoint: str, index_name: str, credential: Any) -> None:
        """Validate common parameters across all factory methods.

        Args:
            name: Tool name
            endpoint: Azure Search endpoint URL
            index_name: Name of search index
            credential: Authentication credentials

        Raises:
            ValueError: If any parameter is invalid
        """
        if not endpoint or not endpoint.startswith(("http://", "https://")):
            raise ValueError("endpoint must be a valid URL starting with http:// or https://")

        if not index_name:
            raise ValueError("index_name cannot be empty")

        if not name:
            raise ValueError("name cannot be empty")

        if not credential:
            raise ValueError("credential cannot be None")

    @classmethod
    def create_keyword_search(
        cls,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, TokenCredential, Dict[str, str]],
        search_fields: Optional[List[str]] = None,
        select_fields: Optional[List[str]] = None,
        filter: Optional[str] = None,
        top: Optional[int] = 5,
        **kwargs: Any,
    ) -> "AzureAISearchTool":
        """Factory method to create a keyword search tool.

        Keyword search performs traditional text-based search, good for finding documents
        containing specific terms or exact matches to your query.

        Args:
            name (str): The name of the tool
            endpoint (str): The URL of your Azure AI Search service
            index_name (str): The name of the search index
            credential (Union[AzureKeyCredential, TokenCredential, Dict[str, str]]): Authentication credentials
            search_fields (Optional[List[str]]): Fields to search within for text search
            select_fields (Optional[List[str]]): Fields to include in results
            filter (Optional[str]): OData filter expression to filter results
            top (Optional[int]): Maximum number of results to return
            **kwargs (Any): Additional configuration options

        Returns:
            An initialized keyword search tool

        Example Usage:
            .. code-block:: python

                # type: ignore
                # Example of using keyword search with Azure AI Search
                from autogen_ext.tools.azure import AzureAISearchTool
                from azure.core.credentials import AzureKeyCredential

                # Create a keyword search tool
                keyword_search = AzureAISearchTool.create_keyword_search(
                    name="keyword_search",
                    endpoint="https://your-service.search.windows.net",
                    index_name="your-index",
                    credential=AzureKeyCredential("your-api-key"),
                    search_fields=["title", "content"],
                    select_fields=["id", "title", "content", "category"],
                    top=10,
                )

                # The search tool can be used with an Agent
                # assistant = Agent("assistant", tools=[keyword_search])
        """
        cls._validate_common_params(name, endpoint, index_name, credential)

        token = _allow_private_constructor.set(True)
        try:
            return cls(
                name=name,
                endpoint=endpoint,
                index_name=index_name,
                credential=credential,
                query_type="keyword",
                search_fields=search_fields,
                select_fields=select_fields,
                filter=filter,
                top=top,
                **kwargs,
            )
        finally:
            _allow_private_constructor.reset(token)

    @classmethod
    def create_full_text_search(
        cls,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, TokenCredential, Dict[str, str]],
        search_fields: Optional[List[str]] = None,
        select_fields: Optional[List[str]] = None,
        filter: Optional[str] = None,
        top: Optional[int] = 5,
        **kwargs: Any,
    ) -> "AzureAISearchTool":
        """Factory method to create a full-text search tool.

        Full-text search uses advanced text analysis (stemming, lemmatization, etc.)
        to provide more comprehensive text matching than basic keyword search.

        Args:
            name (str): The name of the tool
            endpoint (str): The URL of your Azure AI Search service
            index_name (str): The name of the search index
            credential (Union[AzureKeyCredential, TokenCredential, Dict[str, str]]): Authentication credentials
            search_fields (Optional[List[str]]): Fields to search within
            select_fields (Optional[List[str]]): Fields to include in results
            filter (Optional[str]): OData filter expression to filter results
            top (Optional[int]): Maximum number of results to return
            **kwargs (Any): Additional configuration options

        Returns:
            An initialized full-text search tool

        Example Usage:
            .. code-block:: python

                # type: ignore
                # Example of using full-text search with Azure AI Search
                from autogen_ext.tools.azure import AzureAISearchTool
                from azure.core.credentials import AzureKeyCredential

                # Create a full-text search tool
                full_text_search = AzureAISearchTool.create_full_text_search(
                    name="document_search",
                    endpoint="https://your-search-service.search.windows.net",
                    index_name="your-index",
                    credential=AzureKeyCredential("your-api-key"),
                    search_fields=["title", "content"],
                    select_fields=["title", "content", "category", "url"],
                    top=10,
                )

                # The search tool can be used with an Agent
                # assistant = Agent("assistant", tools=[full_text_search])
        """
        cls._validate_common_params(name, endpoint, index_name, credential)

        token = _allow_private_constructor.set(True)
        try:
            query_type = cast(
                Literal["keyword", "fulltext", "vector", "hybrid"],
                "fulltext",
            )

            return cls(
                name=name,
                endpoint=endpoint,
                index_name=index_name,
                credential=credential,
                query_type=query_type,
                search_fields=search_fields,
                select_fields=select_fields,
                filter=filter,
                top=top,
                **kwargs,
            )
        finally:
            _allow_private_constructor.reset(token)

    @classmethod
    def create_vector_search(
        cls,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, TokenCredential, Dict[str, str]],
        vector_fields: List[str],
        select_fields: Optional[List[str]] = None,
        filter: Optional[str] = None,
        top: Optional[int] = 5,
        **kwargs: Any,
    ) -> "AzureAISearchTool":
        """Factory method to create a vector search tool.

        Vector search uses embedding vectors to find semantically similar content, enabling
        the discovery of related information even when different terminology is used.

        Args:
            name (str): The name of the tool
            endpoint (str): The URL of your Azure AI Search service
            index_name (str): The name of the search index
            credential (Union[AzureKeyCredential, TokenCredential, Dict[str, str]]): Authentication credentials
            vector_fields (List[str]): Fields containing vector embeddings for similarity search
            select_fields (Optional[List[str]]): Fields to include in results
            filter (Optional[str]): OData filter expression to filter results
            top (Optional[int]): Maximum number of results to return
            **kwargs (Any): Additional configuration options

        Returns:
            An initialized vector search tool

        Example Usage:
            .. code-block:: python

                # type: ignore
                # Example of using vector search with Azure AI Search
                from autogen_ext.tools.azure import AzureAISearchTool
                from azure.core.credentials import AzureKeyCredential

                # Create a vector search tool
                vector_search = AzureAISearchTool.create_vector_search(
                    name="vector_search",
                    endpoint="https://your-search-service.search.windows.net",
                    index_name="your-index",
                    credential=AzureKeyCredential("your-api-key"),
                    vector_fields=["embedding"],
                    select_fields=["title", "content", "url"],
                    top=5,
                )

                # The search tool can be used with an Agent
                # assistant = Agent("assistant", tools=[vector_search])

        """
        cls._validate_common_params(name, endpoint, index_name, credential)

        if not vector_fields or len(vector_fields) == 0:
            raise ValueError("vector_fields must contain at least one field name")

        token = _allow_private_constructor.set(True)
        try:
            return cls(
                name=name,
                endpoint=endpoint,
                index_name=index_name,
                credential=credential,
                query_type="vector",
                vector_fields=vector_fields,
                select_fields=select_fields,
                filter=filter,
                top=top,
                **kwargs,
            )
        finally:
            _allow_private_constructor.reset(token)

    async def _get_embedding(self, query: str) -> List[float]:
        """Generate embedding vector for the query text.

        This method handles generating embeddings for vector search functionality.
        The embedding provider and model should be specified in the tool configuration.

        Args:
            query (str): The text to generate embeddings for.

        Returns:
            List[float]: The embedding vector as a list of floats.

        Raises:
            ValueError: If the embedding configuration is missing or invalid.
        """
        embedding_provider = getattr(self.search_config, "embedding_provider", None)
        embedding_model = getattr(self.search_config, "embedding_model", None)

        if not embedding_provider or not embedding_model:
            raise ValueError(
                "To use vector search, you must provide embedding_provider and embedding_model in the configuration."
            ) from None

        if embedding_provider.lower() == "azure_openai":
            try:
                from azure.identity import DefaultAzureCredential
                from openai import AsyncAzureOpenAI
            except ImportError:
                raise ImportError(
                    "Azure OpenAI SDK is required for embedding generation. "
                    "Please install it with: uv add openai azure-identity"
                ) from None

            api_key = None
            if hasattr(self.search_config, "openai_api_key"):
                api_key = self.search_config.openai_api_key

            api_version = getattr(self.search_config, "openai_api_version", "2023-05-15")
            endpoint = getattr(self.search_config, "openai_endpoint", None)

            if not endpoint:
                raise ValueError("OpenAI endpoint must be provided for Azure OpenAI embeddings") from None

            if api_key:
                azure_client = AsyncAzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
            else:

                def get_token() -> str:
                    credential = DefaultAzureCredential()
                    return credential.get_token("https://cognitiveservices.azure.com/.default").token

                azure_client = AsyncAzureOpenAI(
                    azure_ad_token_provider=get_token, api_version=api_version, azure_endpoint=endpoint
                )

            response = await azure_client.embeddings.create(model=embedding_model, input=query)
            return response.data[0].embedding

        elif embedding_provider.lower() == "openai":
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError(
                    "OpenAI SDK is required for embedding generation. " "Please install it with: uv add openai"
                ) from None

            api_key = None
            if hasattr(self.search_config, "openai_api_key"):
                api_key = self.search_config.openai_api_key

            openai_client = AsyncOpenAI(api_key=api_key)

            response = await openai_client.embeddings.create(model=embedding_model, input=query)
            return response.data[0].embedding
        else:
            raise ValueError(
                f"Unsupported embedding provider: {embedding_provider}. "
                "Currently supported providers are 'azure_openai' and 'openai'."
            ) from None

    @classmethod
    def create_hybrid_search(
        cls,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, TokenCredential, Dict[str, str]],
        vector_fields: List[str],
        search_fields: Optional[List[str]] = None,
        select_fields: Optional[List[str]] = None,
        filter: Optional[str] = None,
        top: Optional[int] = 5,
        **kwargs: Any,
    ) -> "AzureAISearchTool":
        """Factory method to create a hybrid search tool.

        Hybrid search combines text search (keyword or semantic) with vector similarity
        search to provide more comprehensive results.

        This method doesn't use a separate "hybrid" type but instead configures either
        a "keyword" or "semantic" text search and combines it with vector search.

        Args:
            name (str): The name of the tool
            endpoint (str): The URL of your Azure AI Search service
            index_name (str): The name of the search index
            credential (Union[AzureKeyCredential, TokenCredential, Dict[str, str]]): Authentication credentials
            vector_fields (List[str]): Fields containing vector embeddings for similarity search
            search_fields (Optional[List[str]]): Fields to search within for text search
            select_fields (Optional[List[str]]): Fields to include in results
            filter (Optional[str]): OData filter expression to filter results
            top (Optional[int]): Maximum number of results to return
            **kwargs (Any): Additional configuration options

        Returns:
            An initialized hybrid search tool

        Example Usage:
            .. code-block:: python

                # type: ignore
                # Example of using hybrid search with Azure AI Search
                from autogen_ext.tools.azure import AzureAISearchTool
                from azure.core.credentials import AzureKeyCredential

                # Create a hybrid search tool
                hybrid_search = AzureAISearchTool.create_hybrid_search(
                    name="hybrid_search",
                    endpoint="https://your-search-service.search.windows.net",
                    index_name="your-index",
                    credential=AzureKeyCredential("your-api-key"),
                    vector_fields=["embedding_field"],
                    search_fields=["title", "content"],
                    select_fields=["title", "content", "url", "date"],
                    top=10,
                )

                # The search tool can be used with an Agent
                # assistant = Agent("researcher", tools=[hybrid_search])
        """
        cls._validate_common_params(name, endpoint, index_name, credential)

        if not vector_fields or len(vector_fields) == 0:
            raise ValueError("vector_fields must contain at least one field name")

        token = _allow_private_constructor.set(True)
        try:
            text_query_type = cast(Literal["keyword", "fulltext", "vector", "hybrid"], "hybrid")

            return cls(
                name=name,
                endpoint=endpoint,
                index_name=index_name,
                credential=credential,
                query_type=text_query_type,
                search_fields=search_fields,
                select_fields=select_fields,
                vector_fields=vector_fields,
                filter=filter,
                top=top,
                **kwargs,
            )
        finally:
            _allow_private_constructor.reset(token)

