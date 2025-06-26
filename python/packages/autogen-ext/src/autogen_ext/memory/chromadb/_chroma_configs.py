"""Configuration classes for ChromaDB vector memory."""

from typing import Any, Callable, Dict, Literal, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated


class DefaultEmbeddingFunctionConfig(BaseModel):
    """Configuration for the default ChromaDB embedding function.

    Uses ChromaDB's default embedding function (Sentence Transformers all-MiniLM-L6-v2).

    .. versionadded:: v0.4.1
       Support for custom embedding functions in ChromaDB memory.
    """

    function_type: Literal["default"] = "default"


class SentenceTransformerEmbeddingFunctionConfig(BaseModel):
    """Configuration for SentenceTransformer embedding functions.

    Allows specifying a custom SentenceTransformer model for embeddings.

    .. versionadded:: v0.4.1
       Support for custom embedding functions in ChromaDB memory.

    Args:
        model (str): Name of the SentenceTransformer model to use.
            Defaults to "all-MiniLM-L6-v2".

    Example:
        .. code-block:: python

            config = SentenceTransformerEmbeddingFunctionConfig(model="paraphrase-multilingual-mpnet-base-v2")
    """

    function_type: Literal["sentence_transformer"] = "sentence_transformer"
    model: str = Field(default="all-MiniLM-L6-v2", description="SentenceTransformer model name to use")


class OpenAIEmbeddingFunctionConfig(BaseModel):
    """Configuration for OpenAI embedding functions.

    Uses OpenAI's embedding API for generating embeddings.

    .. versionadded:: v0.4.1
       Support for custom embedding functions in ChromaDB memory.

    Args:
        api_key (str): OpenAI API key. If empty, will attempt to use environment variable.
        model (str): OpenAI embedding model name. Defaults to "text-embedding-3-small".

    Example:
        .. code-block:: python

            config = OpenAIEmbeddingFunctionConfig(api_key="sk-...", model="text-embedding-3-small")
    """

    function_type: Literal["openai"] = "openai"
    api_key: str = Field(default="", description="OpenAI API key")
    model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model name")

class AzureOpenAIEmbeddingFunctionConfig(BaseModel):
    """Configuration for Azure OpenAI embedding functions.
    Uses Azure OpenAI's embedding API for generating embeddings.
    .. versionadded:: v0.4.1
       Support for custom embedding functions in ChromaDB memory.
    Args:
        api_key (str): Azure OpenAI API key. If empty, will attempt to use environment variable.
        api_version (str): Azure OpenAI API version. Defaults to "2024-12-01-preview".
        model (str): Azure OpenAI embedding model name. Defaults to "text-embedding-3-small".
        azure_endpoint (str): Azure OpenAI endpoint URL.
        azure_deployment (str): Azure OpenAI deployment name. Defaults to "text-embedding-3-small".
    Example:
        .. code-block:: python

            config = AzureOpenAIEmbeddingFunctionConfig(
                api_key="your_azure_api_key",
                azure_endpoint="https://your-azure-endpoint.openai.azure.com/",
                azure_deployment="text-embedding-3-small",
                model="text-embedding-3-small"
            )
    """

    function_type: Literal["azure_openai"] = "azure_openai"
    api_type: Literal["azure"] = "azure"
    api_key: str = Field(default="", description="Azure OpenAI API key")
    api_version: str = Field(default="2024-12-01-preview", description="Azure OpenAI API version")
    model: str = Field(default="text-embedding-3-small", description="Azure OpenAI embedding model name")
    azure_endpoint: str = Field(default="", description="Azure OpenAI endpoint URL")
    azure_deployment: str = Field(
        default="",
        description="Azure OpenAI deployment name."
    )

class CustomEmbeddingFunctionConfig(BaseModel):
    """Configuration for custom embedding functions.

    Allows using a custom function that returns a ChromaDB-compatible embedding function.

    .. versionadded:: v0.4.1
       Support for custom embedding functions in ChromaDB memory.

    .. warning::
       Configurations containing custom functions are not serializable.

    Args:
        function (Callable): Function that returns a ChromaDB-compatible embedding function.
        params (Dict[str, Any]): Parameters to pass to the function.

    Example:
        .. code-block:: python

            def create_my_embedder(param1="default"):
                # Return a ChromaDB-compatible embedding function
                class MyCustomEmbeddingFunction(EmbeddingFunction):
                    def __call__(self, input: Documents) -> Embeddings:
                        # Custom embedding logic here
                        return embeddings

                return MyCustomEmbeddingFunction(param1)


            config = CustomEmbeddingFunctionConfig(function=create_my_embedder, params={"param1": "custom_value"})
    """

    function_type: Literal["custom"] = "custom"
    function: Callable[..., Any] = Field(description="Function that returns an embedding function")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to the function")


# Tagged union type for embedding function configurations
EmbeddingFunctionConfig = Annotated[
    Union[
        DefaultEmbeddingFunctionConfig,
        SentenceTransformerEmbeddingFunctionConfig,
        OpenAIEmbeddingFunctionConfig,
        AzureOpenAIEmbeddingFunctionConfig,
        CustomEmbeddingFunctionConfig,
    ],
    Field(discriminator="function_type"),
]


class ChromaDBVectorMemoryConfig(BaseModel):
    """Base configuration for ChromaDB-based memory implementation.

    .. versionchanged:: v0.4.1
       Added support for custom embedding functions via embedding_function_config.
    """

    client_type: Literal["persistent", "http"]
    collection_name: str = Field(default="memory_store", description="Name of the ChromaDB collection")
    distance_metric: str = Field(default="cosine", description="Distance metric for similarity search")
    k: int = Field(default=3, description="Number of results to return in queries")
    score_threshold: float | None = Field(default=None, description="Minimum similarity score threshold")
    allow_reset: bool = Field(default=False, description="Whether to allow resetting the ChromaDB client")
    tenant: str = Field(default="default_tenant", description="Tenant to use")
    database: str = Field(default="default_database", description="Database to use")
    embedding_function_config: EmbeddingFunctionConfig = Field(
        default_factory=DefaultEmbeddingFunctionConfig, description="Configuration for the embedding function"
    )


class PersistentChromaDBVectorMemoryConfig(ChromaDBVectorMemoryConfig):
    """Configuration for persistent ChromaDB memory."""

    client_type: Literal["persistent", "http"] = "persistent"
    persistence_path: str = Field(default="./chroma_db", description="Path for persistent storage")


class HttpChromaDBVectorMemoryConfig(ChromaDBVectorMemoryConfig):
    """Configuration for HTTP ChromaDB memory."""

    client_type: Literal["persistent", "http"] = "http"
    host: str = Field(default="localhost", description="Host of the remote server")
    port: int = Field(default=8000, description="Port of the remote server")
    ssl: bool = Field(default=False, description="Whether to use HTTPS")
    headers: Dict[str, str] | None = Field(default=None, description="Headers to send to the server")
