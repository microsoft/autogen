"""Azure AI Search tool implementation.

This module provides a tool for querying Azure AI Search indexes using various search methods
including text search, semantic search, and vector search.

For more information about Azure AI Search, see:
https://learn.microsoft.com/en-us/azure/search/search-what-is-azure-search
"""

import abc
import asyncio
import logging
import random
import time
import warnings
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Type, TypeVar, Union, cast

from autogen_core import CancellationToken, ComponentModel
from autogen_core.tools import BaseTool
from azure.core.credentials import AzureKeyCredential, TokenCredential
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.search.documents.aio import SearchClient
from pydantic import BaseModel, Field

try:
    from azure.core.pipeline.policies import RetryPolicy

    HAS_RETRY_POLICY = True
except ImportError:
    HAS_RETRY_POLICY = False

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
    import sys

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
    """Tool for performing intelligent search operations using Azure AI Search.

    This is an abstract base class that requires subclasses to implement the _get_embedding method
    for vector search capabilities.

    Azure AI Search (formerly Azure Cognitive Search) provides enterprise-grade search capabilities
    including semantic ranking, vector similarity, and hybrid approaches for optimal information retrieval.

    Key Features:
        * Full-text search with linguistic analysis
        * Semantic search with AI-powered ranking
        * Vector similarity search using embeddings
        * Hybrid search combining multiple approaches
        * Faceted navigation and filtering

    Note:
        The search results from Azure AI Search may contain arbitrary content from the indexed documents.
        Applications should implement appropriate content filtering and validation when displaying results
        to end users.

    External Documentation:
        * Azure AI Search Overview: https://learn.microsoft.com/en-us/azure/search/search-what-is-azure-search
        * REST API Reference: https://learn.microsoft.com/en-us/rest/api/searchservice/
        * Python SDK: https://learn.microsoft.com/en-us/python/api/overview/azure/search-documents-readme

    Args:
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
                retry_policy = RetryPolicy(
                    retry_mode=getattr(self.search_config, "retry_mode", "fixed"),
                    retry_total=getattr(self.search_config, "retry_max_attempts", 3),
                )
                client_args["retry_policy"] = retry_policy

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
                    vectors = [
                        {
                            "value": vector,
                            "fields": field,
                            "k": int(self.search_config.top or 5),
                        }
                        for field in self.search_config.vector_fields
                    ]
                    search_options["vectors"] = vectors

                    if self.search_config.query_type == "vector":
                        text_query = ""

            if cancellation_token.is_cancelled():
                raise Exception("Operation cancelled")

            client = self._get_client()
            results: List[SearchResult] = []

            async with client:
                search_results = await client.search(text_query, **search_options)
                async for doc in search_results:
                    metadata: Dict[str, Any] = {}
                    content: Dict[str, Any] = {}
                    for key, value in doc.items():
                        if key.startswith("@") or key.startswith("_"):
                            metadata[key] = value
                        else:
                            content[key] = value

                    if "@search.score" in doc:
                        score = doc["@search.score"]
                    else:
                        score = 0.0

                    result = SearchResult(
                        score=score,
                        content=content,
                        metadata=metadata,
                    )
                    results.append(result)

            if self.search_config.enable_caching:
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
        return cls(
            name=config.name,
            description=config.description,
            endpoint=config.endpoint,
            index_name=config.index_name,
            api_version=config.api_version,
            credential=config.credential,
            semantic_config_name=config.semantic_config_name,
            query_type=config.query_type,
            search_fields=config.search_fields,
            select_fields=config.select_fields,
            vector_fields=config.vector_fields,
            top=config.top,
        )

    @classmethod
    def load_component(
        cls: Type[T],
        component_config: Union[ComponentModel, Dict[str, Any]],
        component_class: Optional[Type[T]] = None,
    ) -> T:
        """Load the tool from a component model.

        Args:
            component_config (Union[ComponentModel, Dict[str, Any]]): The component configuration.
            component_class (Optional[Type[T]]): Optional component class for deserialization.

        Returns:
            T: An instance of the tool.

        Raises:
            ValueError: If the component configuration is invalid.
        """
        target_class = component_class if component_class is not None else cls

        if hasattr(component_config, "config") and isinstance(component_config.config, dict):
            config_dict = component_config.config
        elif isinstance(component_config, dict):
            config_dict = component_config
        else:
            raise ValueError(f"Invalid component configuration: {component_config}")

        config = AzureAISearchConfig(**config_dict)

        return cast(T, target_class._from_config(config))

    async def run_json(
        self, args: Union[Dict[str, Any], Any], cancellation_token: CancellationToken
    ) -> List[Dict[str, Any]]:
        """Run the tool with JSON arguments and return JSON-serializable results.

        Args:
            args (Union[Dict[str, Any], Any]): The arguments for the tool.
            cancellation_token (CancellationToken): A token that can be used to cancel the operation.

        Returns:
            List[Dict[str, Any]]: A list of search results as dictionaries.
        """
        search_results = await self.run(SearchQuery(**args), cancellation_token)
        return [result.model_dump() for result in search_results.results]

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

        result_strings = []
        for i, result in enumerate(value.results, 1):
            content_str = ", ".join(f"{k}: {v}" for k, v in result.content.items())
            result_strings.append(f"Result {i} (Score: {result.score:.2f}): {content_str}")

        return "\n".join(result_strings)


class OpenAIAzureAISearchTool(BaseAzureAISearchTool):
    """Azure AI Search tool with OpenAI embeddings.

    This implementation uses OpenAI's embedding models to generate vectors for search queries.

    Args:
        openai_client (Union[openai.AsyncOpenAI, openai.AsyncAzureOpenAI]): An initialized async OpenAI client
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
        openai_client: Union["openai.AsyncOpenAI", "openai.AsyncAzureOpenAI"],
        embedding_model: str,
        *args: Any,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

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

    async def _get_embedding(self, query: str) -> List[float]:
        """Generate embedding using OpenAI's async client with retry mechanism.

        This method includes exponential backoff retry logic to handle transient errors
        and rate limiting from the OpenAI API.

        Args:
            query (str): The text to generate embeddings for

        Returns:
            List[float]: The embedding vector as a list of floats

        Raises:
            Exception: If embedding generation fails after retries
        """
        if not query:
            logger.warning("Empty query provided for embedding generation")
            return [0.0] * 1536

        retry_count = 0
        last_exception = None

        while retry_count <= self.max_retries:
            try:
                response = await self.openai_client.embeddings.create(input=query, model=self.embedding_model)
                return response.data[0].embedding

            except Exception as e:
                last_exception = e
                retry_count += 1

                should_retry = False

                if "rate_limit" in str(e).lower() or "too_many_requests" in str(e).lower():
                    should_retry = True
                    logger.warning(f"Rate limit hit with OpenAI API, retrying ({retry_count}/{self.max_retries})")

                elif "connection" in str(e).lower() or "timeout" in str(e).lower():
                    should_retry = True
                    logger.warning(f"Network error with OpenAI API, retrying ({retry_count}/{self.max_retries})")

                elif "server_error" in str(e).lower() or "internal" in str(e).lower():
                    should_retry = True
                    logger.warning(f"Server error with OpenAI API, retrying ({retry_count}/{self.max_retries})")

                if not should_retry or retry_count > self.max_retries:
                    break

                await asyncio.sleep(self.retry_delay * (2 ** (retry_count - 1)) * (0.5 + random.random()))

        logger.error(f"Failed to generate embedding after {self.max_retries} retries: {last_exception}")
        raise Exception(f"Embedding generation failed: {last_exception}") from last_exception

    async def _get_embeddings_batch(self, queries: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple queries in a single request.

        This batched approach is more efficient when processing multiple queries.

        Args:
            queries (List[str]): List of texts to generate embeddings for

        Returns:
            List[List[float]]: List of embedding vectors

        Raises:
            Exception: If embedding generation fails
        """
        if not queries:
            return [[0.0] * 1536] * len(queries)

        non_empty_queries = [q for q in queries if q]
        if not non_empty_queries:
            return [[0.0] * 1536] * len(queries)

        try:
            response = await self.openai_client.embeddings.create(input=non_empty_queries, model=self.embedding_model)

            embeddings = [item.embedding for item in response.data]

            result = []
            empty_vector = [0.0] * 1536

            embedding_idx = 0
            for query in queries:
                if query:
                    result.append(embeddings[embedding_idx])
                    embedding_idx += 1
                else:
                    result.append(empty_vector)

            return result

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise Exception(f"Batch embedding generation failed: {e}") from e

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
        """Factory method to create a semantic search tool.

        Args:
            openai_client (Union["openai.AsyncOpenAI", "openai.AsyncAzureOpenAI"]): The OpenAI client for embeddings
            embedding_model (str): The embedding model to use
            name (str): The name of the tool
            endpoint (str): The Azure AI Search endpoint
            index_name (str): The name of the search index
            credential (Union[AzureKeyCredential, TokenCredential, Dict[str, str]]): The credential for authentication
            semantic_config_name (str): The semantic configuration name
            **kwargs (Any): Additional arguments

        Returns:
            An initialized semantic search tool
        """
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
        """Factory method to create a vector search tool.

        Args:
            openai_client (Union["openai.AsyncOpenAI", "openai.AsyncAzureOpenAI"]): The OpenAI client for embeddings
            embedding_model (str): The embedding model to use
            name (str): The name of the tool
            endpoint (str): The Azure AI Search endpoint
            index_name (str): The name of the search index
            credential (Union[AzureKeyCredential, TokenCredential, Dict[str, str]]): The credential for authentication
            vector_fields (List[str]): The vector fields to search
            **kwargs (Any): Additional arguments

        Returns:
            An initialized vector search tool
        """
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
        """Factory method to create a hybrid search tool (semantic + vector).

        Args:
            openai_client (Union["openai.AsyncOpenAI", "openai.AsyncAzureOpenAI"]): The OpenAI client for embeddings
            embedding_model (str): The embedding model to use
            name (str): The name of the tool
            endpoint (str): The Azure AI Search endpoint
            index_name (str): The name of the search index
            credential (Union[AzureKeyCredential, TokenCredential, Dict[str, str]]): The credential for authentication
            vector_fields (List[str]): The vector fields to search
            semantic_config_name (str): The semantic configuration name
            **kwargs (Any): Additional arguments

        Returns:
            An initialized hybrid search tool
        """
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

    @classmethod
    def from_env(
        cls,
        openai_client: Union["openai.AsyncOpenAI", "openai.AsyncAzureOpenAI"],
        embedding_model: str,
        name: str,
        env_prefix: str = "AZURE_SEARCH",
        **kwargs: Any,
    ) -> "OpenAIAzureAISearchTool":
        """Create a search tool instance from environment variables.

        Args:
            cls (Type): The class to instantiate
            openai_client (Union["openai.AsyncOpenAI", "openai.AsyncAzureOpenAI"]): The OpenAI client for embeddings
            embedding_model (str): The embedding model to use
            name (str): The name of the tool
            env_prefix (str): Prefix for environment variables
            **kwargs (Any): Additional arguments

        Returns:
            An initialized search tool
        """
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
        query_type = os.getenv(f"{env_prefix}_QUERY_TYPE", "simple")

        if query_type not in ["simple", "full", "semantic", "vector"]:
            raise ValueError(f"Invalid query type: {query_type}. Must be one of: simple, full, semantic, vector")

        config_kwargs = {
            "endpoint": endpoint,
            "index_name": index_name,
            "credential": {"api_key": api_key},
            "api_version": api_version,
            "query_type": query_type,
        }

        vector_fields_str = os.getenv(f"{env_prefix}_VECTOR_FIELDS")
        if vector_fields_str:
            config_kwargs["vector_fields"] = [field.strip() for field in vector_fields_str.split(",")]

        semantic_config = os.getenv(f"{env_prefix}_SEMANTIC_CONFIG")
        if semantic_config:
            config_kwargs["semantic_config_name"] = semantic_config

        config_kwargs.update(kwargs)

        search_config = AzureAISearchConfig(**config_kwargs)
        return cls(openai_client=openai_client, embedding_model=embedding_model, name=name, search_config=search_config)
