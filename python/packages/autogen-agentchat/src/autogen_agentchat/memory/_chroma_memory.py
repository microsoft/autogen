from typing import Any, List, Dict
from datetime import datetime
import chromadb
from chromadb.types import Collection
import uuid
import logging
from autogen_core import CancellationToken, Image
from pydantic import Field

from ._base_memory import (
    BaseMemoryConfig,
    Memory,
    MemoryContent,
    MemoryQueryResult,
    MemoryMimeType
)
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage

logger = logging.getLogger(__name__)

# Type vars for ChromaDB results
ChromaMetadata = Dict[str, Any]
ChromaDistance = float | List[float]


class ChromaMemoryConfig(BaseMemoryConfig):
    """Configuration for ChromaDB-based memory implementation."""

    collection_name: str = Field(
        default="memory_store",
        description="Name of the ChromaDB collection"
    )
    persistence_path: str | None = Field(
        default=None,
        description="Path for persistent storage. None for in-memory."
    )
    distance_metric: str = Field(
        default="cosine",
        description="Distance metric for similarity search"
    )


class ChromaMemory(Memory):
    """ChromaDB-based memory implementation using default embeddings.

    This implementation stores content in a ChromaDB collection and uses
    its built-in embedding and similarity search capabilities.
    """

    def __init__(self, name: str | None = None, config: ChromaMemoryConfig | None = None) -> None:
        """Initialize ChromaMemory.

        Args:
            name: Optional identifier for this memory instance
            config: Optional configuration for memory behavior
        """
        self._name = name or "default_chroma_memory"
        self._config = config or ChromaMemoryConfig()
        self._client: chromadb.Client | None = None
        self._collection: Collection | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def config(self) -> ChromaMemoryConfig:
        return self._config

    def _ensure_initialized(self) -> None:
        """Ensure ChromaDB client and collection are initialized."""
        if self._client is None:
            try:
                self._client = (
                    chromadb.PersistentClient(
                        path=self._config.persistence_path)
                    if self._config.persistence_path
                    else chromadb.Client()
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB client: {e}")
                raise

        if self._collection is None and self._client is not None:
            try:
                self._collection = self._client.get_or_create_collection(
                    name=self._config.collection_name,
                    metadata={"distance_metric": self._config.distance_metric}
                )
            except Exception as e:
                logger.error(f"Failed to get/create collection: {e}")
                raise

    def _extract_text(self, content_item: MemoryContent) -> str:
        """Extract searchable text from MemoryContent.

        Args:
            content_item: Content to extract text from

        Returns:
            Extracted text representation

        Raises:
            ValueError: If content cannot be converted to text
        """
        content = content_item.content

        if content_item.mime_type in [MemoryMimeType.TEXT, MemoryMimeType.MARKDOWN]:
            return str(content)
        elif content_item.mime_type == MemoryMimeType.JSON:
            if isinstance(content, dict):
                return str(content)
            raise ValueError("JSON content must be a dict")
        elif isinstance(content, Image):
            raise ValueError("Image content cannot be converted to text")
        else:
            raise ValueError(
                f"Unsupported content type: {content_item.mime_type}")

    async def transform(
        self,
        model_context: ChatCompletionContext,
    ) -> ChatCompletionContext:
        """Transform the model context using relevant memory content.

        Args:
            model_context: The context to transform

        Returns:
            The transformed context with relevant memories added
        """
        messages = await model_context.get_messages()
        if not messages:
            return model_context

        # Extract query from last message
        last_message = messages[-1]
        query_text = last_message.content if isinstance(
            last_message.content, str) else str(last_message)
        query = MemoryContent(content=query_text,
                              mime_type=MemoryMimeType.TEXT)

        # Query memory and format results
        results = []
        query_results = await self.query(query)
        for i, result in enumerate(query_results, 1):
            if isinstance(result.content.content, str):
                results.append(f"{i}. {result.content.content}")
                logger.debug(
                    f"Retrieved memory {i}. {result.content.content}, score: {result.score}"
                )

        # Add memory results to context
        if results:
            memory_context = (
                "Results from memory query to consider include:\n" +
                "\n".join(results)
            )
            await model_context.add_message(SystemMessage(content=memory_context))

        return model_context

    async def add(
        self,
        content: MemoryContent,
        cancellation_token: CancellationToken | None = None
    ) -> None:
        """Add a memory content to ChromaDB.

        Args:
            content: The memory content to add
            cancellation_token: Optional token to cancel operation

        Raises:
            RuntimeError: If ChromaDB initialization fails
        """
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            # Extract text from MemoryContent
            text = self._extract_text(content)

            # Prepare metadata
            metadata: ChromaMetadata = {
                "timestamp": content.timestamp.isoformat() if content.timestamp else datetime.now().isoformat(),
                "source": content.source or "",
                "mime_type": content.mime_type.value,
                **(content.metadata or {})
            }

            # Add to ChromaDB
            self._collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[str(uuid.uuid4())]
            )

        except Exception as e:
            logger.error(f"Failed to add content to ChromaDB: {e}")
            raise

    async def query(
        self,
        query: MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> List[MemoryQueryResult]:
        """Query memory content based on vector similarity.

        Args:
            query: Query content to match against memory
            cancellation_token: Optional token to cancel operation
            **kwargs: Additional parameters passed to ChromaDB query

        Returns:
            List of memory results with similarity scores

        Raises:
            RuntimeError: If ChromaDB initialization fails
        """
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
                **kwargs
            )

            # Convert results to MemoryQueryResults
            memory_results: List[MemoryQueryResult] = []

            if not results["documents"]:
                return memory_results

            for doc, metadata, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            ):
                # Extract stored metadata
                entry_metadata = dict(metadata)
                timestamp_str = str(entry_metadata.pop("timestamp"))
                timestamp = datetime.fromisoformat(timestamp_str)
                source = str(entry_metadata.pop("source"))
                mime_type = MemoryMimeType(entry_metadata.pop("mime_type"))

                # Create MemoryContent
                content = MemoryContent(
                    content=doc,
                    mime_type=mime_type,
                    metadata=entry_metadata,
                    timestamp=timestamp,
                    source=source or None
                )

                # Convert distance to similarity score
                score = 1.0 - (float(distance) / 2.0) if self._config.distance_metric == "cosine" \
                    else 1.0 / (1.0 + float(distance))

                # Apply score threshold if configured
                if self._config.score_threshold is None or score >= self._config.score_threshold:
                    memory_results.append(
                        MemoryQueryResult(content=content, score=score))

            return memory_results

        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            raise

    async def clear(self) -> None:
        """Clear all entries from memory.

        Raises:
            RuntimeError: If ChromaDB initialization fails
        """
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            self._collection.delete()
            if self._client is not None:
                self._collection = self._client.get_or_create_collection(
                    name=self._config.collection_name,
                    metadata={"distance_metric": self._config.distance_metric}
                )
        except Exception as e:
            logger.error(f"Failed to clear ChromaDB collection: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up ChromaDB client and resources."""
        if self._client is not None:
            try:
                if hasattr(self._client, "reset"):
                    self._client.reset()
            except Exception as e:
                logger.error(f"Error during ChromaDB cleanup: {e}")
            finally:
                self._client = None
                self._collection = None
