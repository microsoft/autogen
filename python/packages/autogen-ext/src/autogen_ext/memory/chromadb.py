import logging
import uuid
from typing import Any, Dict, List, Literal

from autogen_core import CancellationToken, Component, Image
from autogen_core.memory import Memory, MemoryContent, MemoryMimeType, MemoryQueryResult, UpdateContextResult
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage
from chromadb import HttpClient, PersistentClient
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Document, Metadata
from pydantic import BaseModel, Field
from typing_extensions import Self

logger = logging.getLogger(__name__)


try:
    from chromadb.api import ClientAPI
except ImportError as e:
    raise ImportError(
        "To use the ChromaDBVectorMemory the chromadb extra must be installed. Run `pip install autogen-ext[chromadb]`"
    ) from e


class ChromaDBVectorMemoryConfig(BaseModel):
    """Base configuration for ChromaDB-based memory implementation."""

    client_type: Literal["persistent", "http"]
    collection_name: str = Field(default="memory_store", description="Name of the ChromaDB collection")
    distance_metric: str = Field(default="cosine", description="Distance metric for similarity search")
    k: int = Field(default=3, description="Number of results to return in queries")
    score_threshold: float | None = Field(default=None, description="Minimum similarity score threshold")
    allow_reset: bool = Field(default=False, description="Whether to allow resetting the ChromaDB client")
    tenant: str = Field(default="default_tenant", description="Tenant to use")
    database: str = Field(default="default_database", description="Database to use")


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


class ChromaDBVectorMemory(Memory, Component[ChromaDBVectorMemoryConfig]):
    """
    Store and retrieve memory using vector similarity search powered by ChromaDB.

    `ChromaDBVectorMemory` provides a vector-based memory implementation that uses ChromaDB for
    storing and retrieving content based on semantic similarity. It enhances agents with the ability
    to recall contextually relevant information during conversations by leveraging vector embeddings
    to find similar content.

    This implementation serves as a reference for more complex memory systems using vector embeddings.
    For advanced use cases requiring specialized formatting of retrieved content, users should extend
    this class and override the `update_context()` method.

    .. note::

        This implementation requires the ChromaDB extra to be installed. Install with:
        `pip install autogen-ext[chromadb]`

    Args:
        config (ChromaDBVectorMemoryConfig | None): Configuration for the ChromaDB memory.
            If None, defaults to a PersistentChromaDBVectorMemoryConfig with default values.
            Two config types are supported:
            - PersistentChromaDBVectorMemoryConfig: For local storage
            - HttpChromaDBVectorMemoryConfig: For connecting to a remote ChromaDB server

    Example:

        .. code-block:: python

            import os
            from pathlib import Path
            from autogen_agentchat.agents import AssistantAgent
            from autogen_core.memory import MemoryContent, MemoryMimeType
            from autogen_ext.memory.chromadb import ChromaDBVectorMemory, PersistentChromaDBVectorMemoryConfig
            from autogen_ext.models.openai import OpenAIChatCompletionClient

            # Initialize ChromaDB memory with custom config
            memory = ChromaDBVectorMemory(
                config=PersistentChromaDBVectorMemoryConfig(
                    collection_name="user_preferences",
                    persistence_path=os.path.join(str(Path.home()), ".chromadb_autogen"),
                    k=3,  # Return top 3 results
                    score_threshold=0.5,  # Minimum similarity score
                )
            )

            # Add user preferences to memory
            await memory.add(
                MemoryContent(
                    content="The user prefers temperatures in Celsius",
                    mime_type=MemoryMimeType.TEXT,
                    metadata={"category": "preferences", "type": "units"},
                )
            )

            # Create assistant agent with ChromaDB memory
            assistant = AssistantAgent(
                name="assistant",
                model_client=OpenAIChatCompletionClient(
                    model="gpt-4o",
                ),
                memory=[memory],
            )

            # The memory will automatically retrieve relevant content during conversations
            stream = assistant.run_stream(task="What's the weather in New York?")

            # Remember to close the memory when finished
            await memory.close()
    """

    component_config_schema = ChromaDBVectorMemoryConfig
    component_provider_override = "autogen_ext.memory.chromadb.ChromaDBVectorMemory"

    def __init__(self, config: ChromaDBVectorMemoryConfig | None = None) -> None:
        """Initialize ChromaDBVectorMemory."""
        self._config = config or PersistentChromaDBVectorMemoryConfig()
        self._client: ClientAPI | None = None
        self._collection: Collection | None = None

    @property
    def collection_name(self) -> str:
        """Get the name of the ChromaDB collection."""
        return self._config.collection_name

    def _ensure_initialized(self) -> None:
        """Ensure ChromaDB client and collection are initialized."""
        if self._client is None:
            try:
                from chromadb.config import Settings

                settings = Settings(allow_reset=self._config.allow_reset)

                if isinstance(self._config, PersistentChromaDBVectorMemoryConfig):
                    self._client = PersistentClient(
                        path=self._config.persistence_path,
                        settings=settings,
                        tenant=self._config.tenant,
                        database=self._config.database,
                    )
                elif isinstance(self._config, HttpChromaDBVectorMemoryConfig):
                    self._client = HttpClient(
                        host=self._config.host,
                        port=self._config.port,
                        ssl=self._config.ssl,
                        headers=self._config.headers,
                        settings=settings,
                        tenant=self._config.tenant,
                        database=self._config.database,
                    )
                else:
                    raise ValueError(f"Unsupported config type: {type(self._config)}")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB client: {e}")
                raise

        if self._collection is None:
            try:
                self._collection = self._client.get_or_create_collection(
                    name=self._config.collection_name, metadata={"distance_metric": self._config.distance_metric}
                )
            except Exception as e:
                logger.error(f"Failed to get/create collection: {e}")
                raise

    def _extract_text(self, content_item: str | MemoryContent) -> str:
        """Extract searchable text from content."""
        if isinstance(content_item, str):
            return content_item

        content = content_item.content
        mime_type = content_item.mime_type

        if mime_type in [MemoryMimeType.TEXT, MemoryMimeType.MARKDOWN]:
            return str(content)
        elif mime_type == MemoryMimeType.JSON:
            if isinstance(content, dict):
                # Store original JSON string representation
                return str(content).lower()
            raise ValueError("JSON content must be a dict")
        elif isinstance(content, Image):
            raise ValueError("Image content cannot be converted to text")
        else:
            raise ValueError(f"Unsupported content type: {mime_type}")

    def _calculate_score(self, distance: float) -> float:
        """Convert ChromaDB distance to a similarity score."""
        if self._config.distance_metric == "cosine":
            return 1.0 - (distance / 2.0)
        return 1.0 / (1.0 + distance)

    async def update_context(
        self,
        model_context: ChatCompletionContext,
    ) -> UpdateContextResult:
        """
        Update the model context with relevant memory content.

        This method retrieves memory content relevant to the last message in the context
        and adds it as a system message. It serves as the primary customization point for
        how retrieved memories are incorporated into the conversation.

        By default, this implementation:
        1. Uses the last message as a query to find semantically similar memories
        2. Formats retrieved memories as a numbered list
        3. Adds them to the context as a system message

        For custom memory formatting, extend this class and override this method.

        Args:
            model_context (ChatCompletionContext): The model context to update with relevant memories.

        Returns:
            UpdateContextResult: Object containing the memories that were used to update the context.

        Example:

            .. code-block:: python

                from autogen_core.memory import Memory, MemoryContent, MemoryQueryResult, UpdateContextResult
                from autogen_core.model_context import ChatCompletionContext
                from autogen_core.models import SystemMessage
                from autogen_ext.memory.chromadb import ChromaDBVectorMemory, PersistentChromaDBVectorMemoryConfig


                class CustomVectorMemory(ChromaDBVectorMemory):
                    async def update_context(
                        self,
                        model_context: ChatCompletionContext,
                    ) -> UpdateContextResult:
                        # Get the last message to use as query
                        messages = await model_context.get_messages()
                        if not messages:
                            return UpdateContextResult(memories=MemoryQueryResult(results=[]))

                        # Get query results
                        last_message = messages[-1]
                        query_text = last_message.content if isinstance(last_message.content, str) else str(last_message)
                        query_results = await self.query(query_text)

                        if query_results.results:
                            # Custom formatting based on memory category
                            memory_strings = []
                            for memory in query_results.results:
                                category = memory.metadata.get("category", "general")
                                if category == "preferences":
                                    memory_strings.append(f"User Preference: {memory.content}")
                                else:
                                    memory_strings.append(f"Memory: {memory.content}")

                            # Add to context with custom header
                            memory_context = "IMPORTANT USER INFORMATION:\n" + "\n".join(memory_strings)
                            await model_context.add_message(SystemMessage(content=memory_context))

                        return UpdateContextResult(memories=query_results)
        """
        messages = await model_context.get_messages()
        if not messages:
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))

        # Extract query from last message
        last_message = messages[-1]
        query_text = last_message.content if isinstance(last_message.content, str) else str(last_message)

        # Query memory and get results
        query_results = await self.query(query_text)

        if query_results.results:
            # Format results for context
            memory_strings = [f"{i}. {str(memory.content)}" for i, memory in enumerate(query_results.results, 1)]
            memory_context = "\nRelevant memory content:\n" + "\n".join(memory_strings)

            # Add to context
            await model_context.add_message(SystemMessage(content=memory_context))

        return UpdateContextResult(memories=query_results)

    async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
        """Add a memory content to ChromaDB."""
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            # Extract text from content
            text = self._extract_text(content)

            # Use metadata directly from content
            metadata_dict = content.metadata or {}
            metadata_dict["mime_type"] = str(content.mime_type)

            # Add to ChromaDB
            self._collection.add(documents=[text], metadatas=[metadata_dict], ids=[str(uuid.uuid4())])

        except Exception as e:
            logger.error(f"Failed to add content to ChromaDB: {e}")
            raise

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """Query memory content based on vector similarity."""
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            # Extract text for query
            query_text = self._extract_text(query)

            # Query ChromaDB
            results = self._collection.query(
                query_texts=[query_text],
                n_results=self._config.k,
                include=["documents", "metadatas", "distances"],
                **kwargs,
            )

            # Convert results to MemoryContent list
            memory_results: List[MemoryContent] = []

            if (
                not results
                or not results.get("documents")
                or not results.get("metadatas")
                or not results.get("distances")
            ):
                return MemoryQueryResult(results=memory_results)

            documents: List[Document] = results["documents"][0] if results["documents"] else []
            metadatas: List[Metadata] = results["metadatas"][0] if results["metadatas"] else []
            distances: List[float] = results["distances"][0] if results["distances"] else []
            ids: List[str] = results["ids"][0] if results["ids"] else []

            for doc, metadata_dict, distance, doc_id in zip(documents, metadatas, distances, ids, strict=False):
                # Calculate score
                score = self._calculate_score(distance)
                metadata = dict(metadata_dict)
                metadata["score"] = score
                metadata["id"] = doc_id
                if self._config.score_threshold is not None and score < self._config.score_threshold:
                    continue

                # Extract mime_type from metadata
                mime_type = str(metadata_dict.get("mime_type", MemoryMimeType.TEXT.value))

                # Create MemoryContent
                content = MemoryContent(
                    content=doc,
                    mime_type=mime_type,
                    metadata=metadata,
                )
                memory_results.append(content)

            return MemoryQueryResult(results=memory_results)

        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            raise

    async def clear(self) -> None:
        """Clear all entries from memory."""
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            results = self._collection.get()
            if results and results["ids"]:
                self._collection.delete(ids=results["ids"])
        except Exception as e:
            logger.error(f"Failed to clear ChromaDB collection: {e}")
            raise

    async def close(self) -> None:
        """Clean up ChromaDB client and resources."""
        self._collection = None
        self._client = None

    async def reset(self) -> None:
        """Reset the memory by deleting all data."""
        self._ensure_initialized()
        if not self._config.allow_reset:
            raise RuntimeError("Reset not allowed. Set allow_reset=True in config to enable.")

        if self._client is not None:
            try:
                self._client.reset()
            except Exception as e:
                logger.error(f"Error during ChromaDB reset: {e}")
            finally:
                self._collection = None

    def _to_config(self) -> ChromaDBVectorMemoryConfig:
        """Serialize the memory configuration."""

        return self._config

    @classmethod
    def _from_config(cls, config: ChromaDBVectorMemoryConfig) -> Self:
        """Deserialize the memory configuration."""

        return cls(config=config)
