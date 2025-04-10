"""Configuration for Azure AI Search tool.

This module provides configuration classes for the Azure AI Search tool, including
settings for authentication, search behavior, retry policies, and caching.
"""

import logging
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
)

from azure.core.credentials import AzureKeyCredential, TokenCredential
from pydantic import BaseModel, Field, model_validator

# Add explicit ignore for the specific model validator error
# pyright: reportArgumentType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownVariableType=false

T = TypeVar("T", bound="AzureAISearchConfig")

logger = logging.getLogger(__name__)


class AzureAISearchConfig(BaseModel):
    """Configuration for Azure AI Search tool.

    This class defines the configuration parameters for :class:`AzureAISearchTool`.
    It provides options for customizing search behavior including query types,
    field selection, authentication, retry policies, and caching strategies.

    .. note::

        This class requires the :code:`azure` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[azure]"

    Example:
        .. code-block:: python

            from azure.core.credentials import AzureKeyCredential
            from autogen_ext.tools.azure import AzureAISearchConfig

            config = AzureAISearchConfig(
                name="doc_search",
                endpoint="https://my-search.search.windows.net",
                index_name="my-index",
                credential=AzureKeyCredential("<your-key>"),
                query_type="vector",
                vector_fields=["embedding"],
            )

    For more details, see:
        * `Azure AI Search Overview <https://learn.microsoft.com/azure/search/search-what-is-azure-search>`_
        * `Vector Search <https://learn.microsoft.com/azure/search/vector-search-overview>`_

    Args:
        name (str): Name for the tool instance, used to identify it in the agent's toolkit.
        description (Optional[str]): Human-readable description of what this tool does and how to use it.
        endpoint (str): The full URL of your Azure AI Search service, in the format
            'https://<service-name>.search.windows.net'.
        index_name (str): Name of the target search index in your Azure AI Search service.
            The index must be pre-created and properly configured.
        api_version (str): Azure AI Search REST API version to use. Defaults to '2023-11-01'.
            Only change if you need specific features from a different API version.
        credential (Union[AzureKeyCredential, TokenCredential]): Azure authentication credential:
            - AzureKeyCredential: For API key authentication (admin/query key)
            - TokenCredential: For Azure AD authentication (e.g., DefaultAzureCredential)
        query_type (Literal["keyword", "fulltext", "vector", "hybrid"]): The search query mode to use:
            - 'keyword': Basic keyword search (default)
            - 'full': Full Lucene query syntax
            - 'vector': Vector similarity search
            - 'hybrid': Hybrid search combining multiple techniques
        search_fields (Optional[List[str]]): List of index fields to search within. If not specified,
            searches all searchable fields. Example: ['title', 'content'].
        select_fields (Optional[List[str]]): Fields to return in search results. If not specified,
            returns all fields. Use to optimize response size.
        vector_fields (Optional[List[str]]): Vector field names for vector search. Must be configured
            in your search index as vector fields. Required for vector search.
        top (Optional[int]): Maximum number of documents to return in search results.
            Helps control response size and processing time.
        retry_enabled (bool): Whether to enable retry policy for transient errors. Defaults to True.
        retry_max_attempts (Optional[int]): Maximum number of retry attempts for failed requests. Defaults to 3.
        retry_mode (Literal["fixed", "exponential"]): Retry backoff strategy: fixed or exponential. Defaults to "exponential".
        enable_caching (bool): Whether to enable client-side caching of search results. Defaults to False.
        cache_ttl_seconds (int): Time-to-live for cached search results in seconds. Defaults to 300 (5 minutes).
        filter (Optional[str]): OData filter expression to refine search results.
    """

    name: str = Field(description="The name of the tool")
    description: Optional[str] = Field(default=None, description="A description of the tool")
    endpoint: str = Field(description="The endpoint URL for your Azure AI Search service")
    index_name: str = Field(description="The name of the search index to query")
    api_version: str = Field(default="2023-11-01", description="API version to use")
    credential: Union[AzureKeyCredential, TokenCredential] = Field(
        description="The credential to use for authentication"
    )
    query_type: Literal["keyword", "fulltext", "vector", "hybrid"] = Field(
        default="keyword", description="Type of query to perform"
    )
    search_fields: Optional[List[str]] = Field(default=None, description="Optional list of fields to search in")
    select_fields: Optional[List[str]] = Field(default=None, description="Optional list of fields to return in results")
    vector_fields: Optional[List[str]] = Field(
        default=None, description="Optional list of vector fields for vector search"
    )
    top: Optional[int] = Field(default=None, description="Optional number of results to return")
    filter: Optional[str] = Field(default=None, description="Optional OData filter expression to refine search results")

    retry_enabled: bool = Field(default=True, description="Whether to enable retry policy for transient errors")
    retry_max_attempts: Optional[int] = Field(
        default=3, description="Maximum number of retry attempts for failed requests"
    )
    retry_mode: Literal["fixed", "exponential"] = Field(
        default="exponential",
        description="Retry backoff strategy: fixed or exponential",
    )

    enable_caching: bool = Field(
        default=False,
        description="Whether to enable client-side caching of search results",
    )
    cache_ttl_seconds: int = Field(
        default=300,  # 5 minutes
        description="Time-to-live for cached search results in seconds",
    )

    embedding_provider: Optional[str] = Field(
        default=None,
        description="Name of embedding provider to use (e.g., 'azure_openai', 'openai')",
    )
    embedding_model: Optional[str] = Field(default=None, description="Model name to use for generating embeddings")
    embedding_dimension: Optional[int] = Field(
        default=None, description="Dimension of embedding vectors produced by the model"
    )

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    @model_validator(mode="before")
    def validate_credentials(cls: Type[T], data: Any) -> Any:
        """Validate and convert credential data."""
        if not isinstance(data, dict):
            return data

        result = {}

        for key, value in data.items():
            result[str(key)] = value

        if "credential" in result:
            credential = result["credential"]

            if isinstance(credential, dict) and "api_key" in credential:
                api_key = str(credential["api_key"])
                result["credential"] = AzureKeyCredential(api_key)

        return result

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        """Custom model_dump to handle credentials."""
        result: Dict[str, Any] = super().model_dump(**kwargs)

        if isinstance(self.credential, AzureKeyCredential):
            result["credential"] = {"type": "AzureKeyCredential"}
        elif isinstance(self.credential, TokenCredential):
            result["credential"] = {"type": "TokenCredential"}

        return result
