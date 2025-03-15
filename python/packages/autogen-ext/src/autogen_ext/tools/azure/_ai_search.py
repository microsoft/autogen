"""Azure AI Search tool implementation.

This module provides a tool for querying Azure AI Search indexes using various search methods
including text search, semantic search, and vector search.

For more information about Azure AI Search, see:
https://learn.microsoft.com/en-us/azure/search/search-what-is-azure-search
"""

import logging
import time
from abc import ABC, abstractmethod
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Type, TypeVar, Union, cast, overload

from autogen_core import CancellationToken, ComponentModel
from autogen_core.tools import BaseTool
from azure.core.credentials import AzureKeyCredential, TokenCredential
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.search.documents.aio import SearchClient
from pydantic import BaseModel, Field

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


if TYPE_CHECKING:
    import openai


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
        self.semantic_config_name = kwargs.get("semantic_config_name", None)
        self.query_type = kwargs.get("query_type", "simple")
        self.search_fields = kwargs.get("search_fields", None)
        self.select_fields = kwargs.get("select_fields", None)
        self.vector_fields = kwargs.get("vector_fields", None)
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

    Args:
        query (str): The search query text.
        vector (Optional[List[float]]): Optional vector for vector/hybrid search.
        filter (Optional[str]): Optional filter expression.
        top (Optional[int]): Optional number of results to return.
    """

    query: str = Field(description="Search query text")
    vector: Optional[List[float]] = Field(default=None, description="Optional vector for vector/hybrid search")
    filter: Optional[str] = Field(default=None, description="Optional filter expression")
    top: Optional[int] = Field(default=None, description="Optional number of results to return")


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
    """A tool for performing searches using Azure AI Search.

    This tool integrates with Azure AI Search to perform different types of searches:
    - Simple text search: Basic keyword matching for straightforward queries
    - Full text search: Enhanced text analysis with language processing
    - Semantic search: Understanding the meaning and context of queries
    - Vector search: Using embeddings for similarity and conceptual matching

    .. note::
        Requires Azure AI Search service and appropriate credentials.
        Compatible with Azure AI Search API versions 2023-07-01-Preview and above.

    .. important::
        For vector search functionality, your Azure AI Search index must contain vector fields
        populated with OpenAI-compatible embeddings. The embeddings in your index should be
        generated using the same or compatible embedding models as specified in this tool.

    Quick Start:
        .. code-block:: python

            # Basic setup with API key
            from autogen_core import ComponentModel
            from autogen_ext.tools.azure import AzureAISearchTool

            # Create search tool with minimal configuration
            search_tool = AzureAISearchTool.load_component(
                ComponentModel(
                    provider="autogen_ext.tools.azure.AzureAISearchTool",
                    config={
                        "name": "AzureSearch",
                        "endpoint": "https://your-search-service.search.windows.net",
                        "index_name": "your-index",
                        "credential": {"api_key": "your-api-key"},
                        "query_type": "simple",
                    },
                )
            )

            # Run a search
            results = await search_tool.run_json(args={"query": "your search query"})
            print(f"Found {len(results.results)} results")

    Examples:
        .. code-block:: python

            # Simple text search example
            from autogen_core import ComponentModel
            from autogen_ext.tools.azure import AzureAISearchTool

            # Create a tool instance with API key
            search_tool = AzureAISearchTool.load_component(
                ComponentModel(
                    provider="autogen_ext.tools.azure.AzureAISearchTool",
                    config={
                        "name": "AzureSearch",
                        "description": "Search documents in Azure AI Search",
                        "endpoint": "https://your-search-service.search.windows.net",
                        "index_name": "your-index",
                        "api_version": "2023-10-01-Preview",
                        "credential": {"api_key": "your-api-key"},
                        "query_type": "simple",
                        "search_fields": ["content", "title"],
                        "select_fields": ["id", "content", "title", "source"],
                        "top": 5,
                    },
                )
            )

            # Run a simple search
            result = await search_tool.run_json(args={"query": "machine learning techniques"})

            # Process results
            for item in result.results:
                print(f"Score: {item.score}, Content: {item.content}")

            # Search with filtering
            filtered_result = await search_tool.run_json(
                args={"query": "neural networks", "filter": "source eq 'academic-papers'"}
            )

        .. code-block:: python

            # Semantic search with OpenAI embeddings
            from openai import AsyncOpenAI

            # Initialize OpenAI client
            openai_client = AsyncOpenAI(api_key="your-openai-api-key")

            # Create semantic search tool
            semantic_search_tool = AzureAISearchTool.load_component(
                ComponentModel(
                    provider="autogen_ext.tools.azure.AzureAISearchTool",
                    config={
                        "name": "SemanticSearch",
                        "description": "Semantic search with Azure AI Search",
                        "endpoint": "https://your-search-service.search.windows.net",
                        "index_name": "your-index",
                        "api_version": "2023-10-01-Preview",
                        "credential": {"api_key": "your-api-key"},
                        "query_type": "semantic",
                        "semantic_config_name": "your-semantic-config",
                        "search_fields": ["content", "title"],
                        "select_fields": ["id", "content", "title", "source"],
                        "openai_client": openai_client,
                        "embedding_model": "text-embedding-ada-002",
                        "top": 5,
                    },
                )
            )

            # Perform a semantic search
            try:
                result = await semantic_search_tool.run_json(args={"query": "latest advances in neural networks"})
                print(f"Found {len(result.results)} results")
            except Exception as e:
                print(f"Search error: {e}")

        .. code-block:: python

            # Vector search example
            # Create vector search tool
            vector_search_tool = AzureAISearchTool.load_component(
                ComponentModel(
                    provider="autogen_ext.tools.azure.AzureAISearchTool",
                    config={
                        "name": "VectorSearch",
                        "description": "Vector search with Azure AI Search",
                        "endpoint": "https://your-search-service.search.windows.net",
                        "index_name": "your-index",
                        "api_version": "2023-10-01-Preview",
                        "credential": {"api_key": "your-api-key"},
                        "query_type": "vector",
                        "vector_fields": ["embedding"],
                        "select_fields": ["id", "content", "title", "source"],
                        "openai_client": openai_client,
                        "embedding_model": "text-embedding-ada-002",
                        "top": 5,
                    },
                )
            )

            # Perform a vector search with a text query (will be converted to vector)
            result = await vector_search_tool.run_json(args={"query": "quantum computing algorithms"})

            # Or use a pre-computed vector directly
            vector = [0.1, 0.2, 0.3, 0.4]  # Example vector (would be much longer in practice)
            result = await vector_search_tool.run_json(args={"vector": vector})

    Using with AutoGen Agents:
        .. code-block:: python

            # Set up the search tool with an agent
            from autogen import ConversableAgent
            from autogen_core import ComponentModel
            from autogen_ext.tools.azure import AzureAISearchTool

            # Create the search tool
            search_tool = AzureAISearchTool.load_component(
                ComponentModel(
                    provider="autogen_ext.tools.azure.AzureAISearchTool",
                    config={
                        "name": "DocumentSearch",
                        "endpoint": "https://your-search-service.search.windows.net",
                        "index_name": "your-index",
                        "credential": {"api_key": "your-api-key"},
                        "query_type": "semantic",
                        "openai_client": openai_client,
                        "embedding_model": "text-embedding-ada-002",
                    },
                )
            )

            # Create an assistant with the search tool
            assistant = ConversableAgent(
                name="research_assistant",
                llm_config={"config_list": [...], "tools": [search_tool.schema]},
                system_message="You are a research assistant with access to a document search tool.",
            )

            # The agent can now use search in conversations
            user = ConversableAgent(name="user")
            user.initiate_chat(assistant, message="Find information about quantum computing applications")

    Result Structure:
        The search results are returned as a `SearchResults` object containing:

        .. code-block:: python

            class SearchResults(BaseModel):
                results: List[SearchResult]


            class SearchResult(BaseModel):
                score: float  # Relevance score (0.0-1.0)
                content: Dict[str, Any]  # Document content fields
                metadata: Dict[str, Any]  # System metadata

    Troubleshooting:
        - If you receive authentication errors, verify your credential is correct
        - For "index not found" errors, check that the index name exists in your Azure service
        - For performance issues, consider using vector search with pre-computed embeddings
        - Rate limits may apply based on your Azure service tier

    External Resources:
        - `Azure AI Search Documentation <https://learn.microsoft.com/en-us/azure/search/search-what-is-azure-search>`_
        - `Create an Azure AI Search Index <https://learn.microsoft.com/en-us/azure/search/search-get-started-portal>`_
        - `Azure AI Search Vector Search <https://learn.microsoft.com/en-us/azure/search/vector-search-overview>`_

    Args:
        embedding_model (str): The name of the embedding model to use
        name (str): Name for the tool instance.
        endpoint (str): The full URL of your Azure AI Search service.
        index_name (str): Name of the search index to query.
        credential (Union[AzureKeyCredential, TokenCredential, Dict[str, str]]): Azure credential for authentication.
        description (Optional[str]): Optional description explaining the tool's purpose.
        api_version (str): Azure AI Search API version to use.
        semantic_config_name (Optional[str]): Name of the semantic configuration.
        query_type (str): The type of search to perform ("simple", "full", "semantic", "vector").
        search_fields (Optional[List[str]]): Fields to search within documents.
        select_fields (Optional[List[str]]): Fields to return in search results.
        vector_fields (Optional[List[str]]): Fields to use for vector search.
        top (Optional[int]): Maximum number of results to return.
        max_retries (int): Maximum number of retries for OpenAI API calls (default: 3)
        retry_delay (float): Base delay in seconds between retries (default: 1.0)
    """

    def __init__(
        self,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, TokenCredential, Dict[str, str]],
        description: Optional[str] = None,
        api_version: str = "2023-11-01",
        semantic_config_name: Optional[str] = None,
        query_type: Literal["simple", "full", "semantic", "vector"] = "simple",
        search_fields: Optional[List[str]] = None,
        select_fields: Optional[List[str]] = None,
        vector_fields: Optional[List[str]] = None,
        top: Optional[int] = None,
    ):
        """Initialize the Azure AI Search tool."""
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

        if isinstance(credential, dict) and "api_key" in credential:
            actual_credential: Union[AzureKeyCredential, TokenCredential] = AzureKeyCredential(credential["api_key"])
        else:
            actual_credential = cast(Union[AzureKeyCredential, TokenCredential], credential)

        self.search_config = AzureAISearchConfig(
            name=name,
            description=description,
            endpoint=endpoint,
            index_name=index_name,
            credential=actual_credential,
            api_version=api_version,
            semantic_config_name=semantic_config_name,
            query_type=query_type,
            search_fields=search_fields,
            select_fields=select_fields,
            vector_fields=vector_fields,
            top=top,
        )

        self._endpoint = endpoint
        self._index_name = index_name
        self._credential = credential
        self._api_version = api_version
        self._client: Optional[SearchClient] = None
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _get_client(self) -> SearchClient:
        """Initialize and return the search client."""
        if self._client is None:
            client_args: Dict[str, Any] = {
                "endpoint": self._endpoint,
                "index_name": self._index_name,
                "credential": self._credential,
                "api_version": self._api_version,
            }

            if HAS_RETRY_POLICY and getattr(self.search_config, "retry_enabled", False):
                try:
                    retry_policy: Any = RetryPolicy(
                        retry_mode=getattr(self.search_config, "retry_mode", "fixed"),
                        retry_total=getattr(self.search_config, "retry_max_attempts", 3),
                    )
                    client_args["retry_policy"] = retry_policy
                except Exception as e:
                    logging.warning(f"Failed to create RetryPolicy: {e}")

            self._client = SearchClient(**client_args)

        assert self._client is not None
        return self._client

    async def run(self, args: SearchQuery, cancellation_token: CancellationToken) -> SearchResults:
        """Run the search query.

        Args:
            args (SearchQuery): The search query parameters, including:
                - query (str): The search query text
                - vector (Optional[List[float]]): Optional vector for vector/hybrid search
                - filter (Optional[str]): Optional filter expression
                - top (Optional[int]): Optional number of results to return
            cancellation_token (CancellationToken): Token for cancelling the operation.

        Returns:
            List[SearchResult]: A list of search results, each containing:
                - score (float): The search relevance score
                - content (Dict[str, Any]): The document content
                - metadata (Dict[str, Any]): Additional metadata about the document

        Raises:
            Exception: If the search operation fails, with detailed error messages for common issues.
        """
        try:
            if cancellation_token.is_cancelled():
                raise Exception("Operation cancelled")

            if self.search_config.enable_caching:
                cache_key = f"{args.query}:{args.filter}:{args.top}:{args.vector}"
                if cache_key in self._cache:
                    cache_entry = self._cache[cache_key]
                    cache_age = time.time() - cache_entry["timestamp"]
                    if cache_age < self.search_config.cache_ttl_seconds:
                        logger.debug(f"Using cached results for query: {args.query}")
                        return SearchResults(results=cache_entry["results"])

            search_options: Dict[str, Any] = {}
            search_options["query_type"] = self.search_config.query_type

            if self.search_config.select_fields:
                search_options["select"] = self.search_config.select_fields

            if self.search_config.search_fields:
                search_options["search_fields"] = self.search_config.search_fields

            if args.filter:
                search_options["filter"] = args.filter

            if args.top is not None:
                search_options["top"] = args.top
            elif self.search_config.top is not None:
                search_options["top"] = self.search_config.top

            if self.search_config.query_type == "semantic" and self.search_config.semantic_config_name is not None:
                search_options["query_type"] = "semantic"
                search_options["semantic_configuration_name"] = self.search_config.semantic_config_name

            text_query = args.query
            if (
                self.search_config.query_type == "vector"
                or args.vector
                or (self.search_config.vector_fields and len(self.search_config.vector_fields) > 0)
            ):
                vector = args.vector
                if vector is None:
                    vector = await self._get_embedding(args.query)

                if self.search_config.vector_fields:
                    vector_fields_list = self.search_config.vector_fields
                    search_options["vectors"] = [
                        {
                            "value": vector,
                            "fields": ",".join(vector_fields_list),
                            "k": int(self.search_config.top or 5),
                        }
                    ]

            if cancellation_token.is_cancelled():
                raise Exception("Operation cancelled")

            client = self._get_client()
            results: List[SearchResult] = []

            async with client:
                search_results = await client.search(text_query, **search_options)  # type: ignore
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
                cache_key = f"{text_query}_{args.filter}_{args.top}"
                vector_part = ""
                try:
                    vector_arg = getattr(args, "vector", None)
                    if vector_arg is not None:
                        vector_sample = vector_arg[:3] if len(vector_arg) > 3 else vector_arg
                        vector_elements = [str(float(v)) for v in vector_sample]
                        vector_part = f"_vector_{','.join(vector_elements)}"
                except (AttributeError, TypeError, ValueError):
                    pass

                cache_key = f"{cache_key}{vector_part}"
                self._cache[cache_key] = {"results": results, "timestamp": time.time()}

            return SearchResults(results=results)

        except Exception as e:
            if isinstance(e, ResourceNotFoundError) or "ResourceNotFoundError" in str(type(e)):
                error_msg = str(e)
                if "test-index" in error_msg or self.search_config.index_name in error_msg:
                    raise Exception(
                        f"Index '{self.search_config.index_name}' not found - Please verify the index name is correct and exists in your Azure AI Search service"
                    ) from e
                elif "cognitive-services" in error_msg.lower():
                    raise Exception(
                        f"Azure AI Search service not found - Please verify your endpoint URL is correct: {e}"
                    ) from e
                else:
                    raise Exception(f"Azure AI Search resource not found: {e}") from e

            elif isinstance(e, HttpResponseError) or "HttpResponseError" in str(type(e)):
                error_msg = str(e)
                if "invalid_api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                    raise Exception(
                        "Authentication failed: Invalid API key or credentials - Please verify your credentials are correct"
                    ) from e
                elif "syntax_error" in error_msg.lower():
                    raise Exception(
                        f"Invalid query syntax - Please check your search query format: {args.query}"
                    ) from e
                elif "bad request" in error_msg.lower():
                    raise Exception(f"Bad request - The search request contains invalid parameters: {e}") from e
                elif "timeout" in error_msg.lower():
                    raise Exception(
                        "Azure AI Search operation timed out - Consider simplifying your query or checking service health"
                    ) from e
                elif "service unavailable" in error_msg.lower():
                    raise Exception("Azure AI Search service is currently unavailable - Please try again later") from e
                else:
                    raise Exception(f"Azure AI Search HTTP error: {e}") from e

            elif cancellation_token.is_cancelled():
                raise Exception("Operation cancelled") from None

            else:
                logger.error(f"Unexpected error during search operation: {e}")
                raise Exception(
                    f"Error during search operation: {e} - Please check your search configuration and Azure AI Search service status"
                ) from e

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
        query_type_str = getattr(config, "query_type", "simple")
        query_type: Literal["simple", "full", "semantic", "vector"]

        if query_type_str == "simple":
            query_type = "simple"
        elif query_type_str == "full":
            query_type = "full"
        elif query_type_str == "semantic":
            query_type = "semantic"
        elif query_type_str == "vector":
            query_type = "vector"
        else:
            query_type = "simple"

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
            semantic_config_name=getattr(config, "semantic_config_name", None),
            query_type=query_type,
            search_fields=getattr(config, "search_fields", None),
            select_fields=getattr(config, "select_fields", None),
            vector_fields=getattr(config, "vector_fields", None),
            top=getattr(config, "top", None),
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


class OpenAIAzureAISearchTool(BaseAzureAISearchTool):
    """A tool for performing searches using Azure AI Search with OpenAI embeddings.

    This tool extends the base Azure AI Search tool with OpenAI embedding capabilities
    for generating vector embeddings at query time.

    Note:
        Do not initialize this class directly. Use factory methods like
        create_semantic_search(), create_vector_search(), or load_component() instead.
    """

    def __init__(
        self,
        openai_client: Union["openai.AsyncOpenAI", "openai.AsyncAzureOpenAI"],
        embedding_model: str,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, TokenCredential, Dict[str, str]],
        description: Optional[str] = None,
        api_version: str = "2023-11-01",
        semantic_config_name: Optional[str] = None,
        query_type: Literal["simple", "full", "semantic", "vector"] = "simple",
        search_fields: Optional[List[str]] = None,
        select_fields: Optional[List[str]] = None,
        vector_fields: Optional[List[str]] = None,
        top: Optional[int] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        if not _allow_private_constructor.get():
            raise RuntimeError(
                "Constructor is private. Use factory methods like create_semantic_search(), "
                "create_vector_search(), or load_component() instead."
            )

        super().__init__(
            name=name,
            endpoint=endpoint,
            index_name=index_name,
            credential=credential,
            description=description,
            api_version=api_version,
            semantic_config_name=semantic_config_name,
            query_type=query_type,
            search_fields=search_fields,
            select_fields=select_fields,
            vector_fields=vector_fields,
            top=top,
        )

        if not openai_client:
            raise ValueError("openai_client must be provided")
        if not embedding_model:
            raise ValueError("embedding_model must be specified")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if retry_delay <= 0:
            raise ValueError("retry_delay must be positive")

        self.openai_client = openai_client
        self.embedding_model = embedding_model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @classmethod
    @overload
    def load_component(
        cls, model: Union[ComponentModel, Dict[str, Any]], expected: None = None
    ) -> "OpenAIAzureAISearchTool": ...

    @classmethod
    @overload
    def load_component(
        cls, model: Union[ComponentModel, Dict[str, Any]], expected: Type[ExpectedType]
    ) -> ExpectedType: ...

    @classmethod
    def load_component(
        cls, model: Union[ComponentModel, Dict[str, Any]], expected: Optional[Type[ExpectedType]] = None
    ) -> Union["OpenAIAzureAISearchTool", ExpectedType]:
        """Load a component from a component model.

        Args:
            model: The component model or dictionary with configuration
            expected: Optional expected return type

        Returns:
            An initialized OpenAIAzureAISearchTool instance
        """
        token = _allow_private_constructor.set(True)
        try:
            if isinstance(model, dict):
                model = ComponentModel(**model)

            config = model.config

            query_type_str = config.get("query_type", "simple")
            query_type: Literal["simple", "full", "semantic", "vector"]

            if query_type_str == "simple":
                query_type = "simple"
            elif query_type_str == "full":
                query_type = "full"
            elif query_type_str == "semantic":
                query_type = "semantic"
            elif query_type_str == "vector":
                query_type = "vector"
            else:
                query_type = "simple"

            openai_client = config.get("openai_client")
            if openai_client is None:
                raise ValueError("openai_client must be provided in config")

            embedding_model = config.get("embedding_model", "")
            if not embedding_model:
                raise ValueError("embedding_model must be specified in config")

            instance = cls(
                openai_client=openai_client,
                embedding_model=embedding_model,
                name=config.get("name", ""),
                endpoint=config.get("endpoint", ""),
                index_name=config.get("index_name", ""),
                credential=config.get("credential", {}),
                description=config.get("description"),
                api_version=config.get("api_version", "2023-11-01"),
                semantic_config_name=config.get("semantic_config_name"),
                query_type=query_type,
                search_fields=config.get("search_fields"),
                select_fields=config.get("select_fields"),
                vector_fields=config.get("vector_fields"),
                top=config.get("top"),
                max_retries=config.get("max_retries", 3),
                retry_delay=config.get("retry_delay", 1.0),
            )

            if expected is not None:
                return cast(ExpectedType, instance)
            return instance
        finally:
            _allow_private_constructor.reset(token)

    @classmethod
    def create_semantic_search(
        cls,
        openai_client: Union["openai.AsyncOpenAI", "openai.AsyncAzureOpenAI"],
        embedding_model: str,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, TokenCredential, Dict[str, str]],
        semantic_config_name: str,
        **kwargs: Any,
    ) -> "OpenAIAzureAISearchTool":
        """Factory method to create a semantic search tool."""
        token = _allow_private_constructor.set(True)
        try:
            return cls(
                openai_client=openai_client,
                embedding_model=embedding_model,
                name=name,
                endpoint=endpoint,
                index_name=index_name,
                credential=credential,
                query_type="semantic",
                semantic_config_name=semantic_config_name,
                **kwargs,
            )
        finally:
            _allow_private_constructor.reset(token)

    @classmethod
    def create_vector_search(
        cls,
        openai_client: Union["openai.AsyncOpenAI", "openai.AsyncAzureOpenAI"],
        embedding_model: str,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, TokenCredential, Dict[str, str]],
        vector_fields: List[str],
        **kwargs: Any,
    ) -> "OpenAIAzureAISearchTool":
        """Factory method to create a vector search tool."""
        token = _allow_private_constructor.set(True)
        try:
            return cls(
                openai_client=openai_client,
                embedding_model=embedding_model,
                name=name,
                endpoint=endpoint,
                index_name=index_name,
                credential=credential,
                query_type="vector",
                vector_fields=vector_fields,
                **kwargs,
            )
        finally:
            _allow_private_constructor.reset(token)

    @classmethod
    def create_hybrid_search(
        cls,
        openai_client: Union["openai.AsyncOpenAI", "openai.AsyncAzureOpenAI"],
        embedding_model: str,
        name: str,
        endpoint: str,
        index_name: str,
        credential: Union[AzureKeyCredential, TokenCredential, Dict[str, str]],
        vector_fields: List[str],
        semantic_config_name: str,
        **kwargs: Any,
    ) -> "OpenAIAzureAISearchTool":
        """Factory method to create a hybrid search tool."""
        token = _allow_private_constructor.set(True)
        try:
            return cls(
                openai_client=openai_client,
                embedding_model=embedding_model,
                name=name,
                endpoint=endpoint,
                index_name=index_name,
                credential=credential,
                query_type="semantic",
                vector_fields=vector_fields,
                semantic_config_name=semantic_config_name,
                **kwargs,
            )
        finally:
            _allow_private_constructor.reset(token)

    @classmethod
    def from_env(
        cls,
        openai_client: Union["openai.AsyncOpenAI", "openai.AsyncAzureOpenAI"],
        embedding_model: str,
        name: str,
        env_prefix: str = "AZURE_SEARCH",
        **kwargs: Any,
    ) -> "OpenAIAzureAISearchTool":
        """Create a search tool instance from environment variables."""
        token = _allow_private_constructor.set(True)
        try:
            import os

            endpoint = os.getenv(f"{env_prefix}_ENDPOINT")
            index_name = os.getenv(f"{env_prefix}_INDEX_NAME")
            api_key = os.getenv(f"{env_prefix}_API_KEY")

            if not endpoint or not index_name or not api_key:
                raise ValueError(
                    f"Missing required environment variables. Please set {env_prefix}_ENDPOINT, "
                    f"{env_prefix}_INDEX_NAME, and {env_prefix}_API_KEY."
                )

            api_version = os.getenv(f"{env_prefix}_API_VERSION", "2023-11-01")
            query_type_str = os.getenv(f"{env_prefix}_QUERY_TYPE", "simple")

            valid_query_types = ["simple", "full", "semantic", "vector"]
            if query_type_str not in valid_query_types:
                raise ValueError(
                    f"Invalid query type: {query_type_str}. Must be one of: {', '.join(valid_query_types)}"
                )

            query_type: Literal["simple", "full", "semantic", "vector"]
            if query_type_str == "simple":
                query_type = "simple"
            elif query_type_str == "full":
                query_type = "full"
            elif query_type_str == "semantic":
                query_type = "semantic"
            else:
                query_type = "vector"

            credential = {"api_key": api_key}

            vector_fields = None
            vector_fields_str = os.getenv(f"{env_prefix}_VECTOR_FIELDS")
            if vector_fields_str:
                vector_fields = vector_fields_str.split(",")

            semantic_config_name = os.getenv(f"{env_prefix}_SEMANTIC_CONFIG")

            additional_params = kwargs.copy()

            return cls(
                openai_client=openai_client,
                embedding_model=embedding_model,
                name=name,
                endpoint=endpoint,
                index_name=index_name,
                credential=credential,
                api_version=api_version,
                query_type=query_type,
                vector_fields=vector_fields,
                semantic_config_name=semantic_config_name,
                **additional_params,
            )
        finally:
            _allow_private_constructor.reset(token)
