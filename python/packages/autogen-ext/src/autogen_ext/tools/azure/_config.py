"""Configuration for Azure AI Search tool.

This module provides configuration classes for the Azure AI Search tool, including
settings for authentication, search behavior, retry policies, and caching.
"""

import logging
from typing import (
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
)

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from pydantic import BaseModel, Field, field_validator, model_validator

T = TypeVar("T", bound="AzureAISearchConfig")

logger = logging.getLogger(__name__)

QueryTypeLiteral = Literal["simple", "full", "semantic", "vector"]
DEFAULT_API_VERSION = "2023-10-01-preview"


class AzureAISearchConfig(BaseModel):
    """Configuration for Azure AI Search with validation.

    This class defines the configuration parameters for Azure AI Search tools, including
    authentication, search behavior, caching, and embedding settings.

    .. note::
        This class requires the ``azure`` extra for the ``autogen-ext`` package.

        .. code-block:: bash

            pip install -U "autogen-ext[azure]"

    .. note::
        **Prerequisites:**

        1. An Azure AI Search service must be created in your Azure subscription.
        2. The search index must be properly configured for your use case:

           - For vector search: Index must have vector fields
           - For semantic search: Index must have semantic configuration
           - For hybrid search: Both vector fields and text fields must be configured
        3. Required packages:

           - Base functionality: ``azure-search-documents>=11.4.0``
           - For Azure OpenAI embeddings: ``openai azure-identity``
           - For OpenAI embeddings: ``openai``

    Example Usage:
        .. code-block:: python

            from azure.core.credentials import AzureKeyCredential
            from autogen_ext.tools.azure import AzureAISearchConfig

            # Basic configuration for full-text search
            config = AzureAISearchConfig(
                name="doc-search",
                endpoint="https://your-search.search.windows.net",  # Your Azure AI Search endpoint
                index_name="<your-index>",  # Name of your search index
                credential=AzureKeyCredential("<your-key>"),  # Your Azure AI Search admin key
                query_type="simple",
                search_fields=["content", "title"],  # Update with your searchable fields
                top=5,
            )

            # Configuration for vector search with Azure OpenAI embeddings
            vector_config = AzureAISearchConfig(
                name="vector-search",
                endpoint="https://your-search.search.windows.net",
                index_name="<your-index>",
                credential=AzureKeyCredential("<your-key>"),
                query_type="vector",
                vector_fields=["embedding"],  # Update with your vector field name
                embedding_provider="azure_openai",
                embedding_model="text-embedding-ada-002",
                openai_endpoint="https://your-openai.openai.azure.com",  # Your Azure OpenAI endpoint
                openai_api_key="<your-openai-key>",  # Your Azure OpenAI key
                top=5,
            )

            # Configuration for hybrid search with semantic ranking
            hybrid_config = AzureAISearchConfig(
                name="hybrid-search",
                endpoint="https://your-search.search.windows.net",
                index_name="<your-index>",
                credential=AzureKeyCredential("<your-key>"),
                query_type="semantic",
                semantic_config_name="<your-semantic-config>",  # Name of your semantic configuration
                search_fields=["content", "title"],  # Update with your search fields
                vector_fields=["embedding"],  # Update with your vector field name
                embedding_provider="openai",
                embedding_model="text-embedding-ada-002",
                openai_api_key="<your-openai-key>",  # Your OpenAI API key
                top=5,
            )
    """

    name: str = Field(description="The name of this tool instance")
    description: Optional[str] = Field(default=None, description="Description explaining the tool's purpose")
    endpoint: str = Field(description="The full URL of your Azure AI Search service")
    index_name: str = Field(description="Name of the search index to query")
    credential: Union[AzureKeyCredential, AsyncTokenCredential] = Field(
        description="Azure credential for authentication (API key or token)"
    )
    api_version: str = Field(
        default=DEFAULT_API_VERSION,
        description=f"Azure AI Search API version to use. Defaults to {DEFAULT_API_VERSION}.",
    )
    query_type: QueryTypeLiteral = Field(
        default="simple", description="Type of search to perform: simple, full, semantic, or vector"
    )
    search_fields: Optional[List[str]] = Field(default=None, description="Fields to search within documents")
    select_fields: Optional[List[str]] = Field(default=None, description="Fields to return in search results")
    vector_fields: Optional[List[str]] = Field(default=None, description="Fields to use for vector search")
    top: Optional[int] = Field(
        default=None, description="Maximum number of results to return. For vector searches, acts as k in k-NN."
    )
    filter: Optional[str] = Field(default=None, description="OData filter expression to refine search results")
    semantic_config_name: Optional[str] = Field(
        default=None, description="Semantic configuration name for enhanced results"
    )

    enable_caching: bool = Field(default=False, description="Whether to cache search results")
    cache_ttl_seconds: int = Field(default=300, description="How long to cache results in seconds")

    embedding_provider: Optional[str] = Field(
        default=None, description="Name of embedding provider for client-side embeddings"
    )
    embedding_model: Optional[str] = Field(default=None, description="Model name for client-side embeddings")
    openai_api_key: Optional[str] = Field(default=None, description="API key for OpenAI/Azure OpenAI embeddings")
    openai_api_version: Optional[str] = Field(default=None, description="API version for Azure OpenAI embeddings")
    openai_endpoint: Optional[str] = Field(default=None, description="Endpoint URL for Azure OpenAI embeddings")

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("endpoint")
    def validate_endpoint(cls, v: str) -> str:
        """Validate that the endpoint is a valid URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("endpoint must be a valid URL starting with http:// or https://")
        return v

    @field_validator("query_type")
    def normalize_query_type(cls, v: QueryTypeLiteral) -> QueryTypeLiteral:
        """Normalize query type to standard values."""
        if not v:
            return "simple"

        if isinstance(v, str) and v.lower() == "fulltext":
            return "full"

        return v

    @field_validator("top")
    def validate_top(cls, v: Optional[int]) -> Optional[int]:
        """Ensure top is a positive integer if provided."""
        if v is not None and v <= 0:
            raise ValueError("top must be a positive integer")
        return v

    @model_validator(mode="after")
    def validate_interdependent_fields(self) -> "AzureAISearchConfig":
        """Validate interdependent fields after all fields have been parsed."""
        if self.query_type == "semantic" and not self.semantic_config_name:
            raise ValueError("semantic_config_name must be provided when query_type is 'semantic'")

        if self.query_type == "vector" and not self.vector_fields:
            raise ValueError("vector_fields must be provided for vector search")

        if (
            self.embedding_provider
            and self.embedding_provider.lower() == "azure_openai"
            and self.embedding_model
            and not self.openai_endpoint
        ):
            raise ValueError("openai_endpoint must be provided for azure_openai embedding provider")

        return self
