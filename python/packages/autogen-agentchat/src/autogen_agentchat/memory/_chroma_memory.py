from typing import Any, List, Optional, Dict
from types import TracebackType
from datetime import datetime
import chromadb
from chromadb.types import Collection
import uuid
import logging
from autogen_core import CancellationToken, Image
from pydantic import Field

from ._base_memory import BaseMemoryConfig, Memory, MemoryEntry, MemoryQueryResult, MemoryContent, MimeType
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage

logger = logging.getLogger(__name__)

# Type vars for ChromaDB results
ChromaMetadata = Dict[str, Any]
ChromaDistance = float | List[float]


class ChromaMemoryConfig(BaseMemoryConfig):
    """Configuration for ChromaDB-based memory implementation."""

    collection_name: str = Field(default="memory_store", description="Name of the ChromaDB collection")
    persistence_path: str | None = Field(default=None, description="Path for persistent storage. None for in-memory.")
    distance_metric: str = Field(default="cosine", description="Distance metric for similarity search")


class ChromaMemory(Memory):
    """ChromaDB-based memory implementation using default embeddings."""

    def __init__(self, name: str | None = None, config: ChromaMemoryConfig | None = None) -> None:
        """Initialize ChromaMemory."""
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
                    chromadb.PersistentClient(path=self._config.persistence_path)
                    if self._config.persistence_path
                    else chromadb.Client()
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB client: {e}")
                raise

        if self._collection is None and self._client is not None:
            try:
                self._collection = self._client.get_or_create_collection(
                    name=self._config.collection_name, metadata={"distance_metric": self._config.distance_metric}
                )
            except Exception as e:
                logger.error(f"Failed to get/create collection: {e}")
                raise

    def _extract_text(self, content_item: MemoryContent) -> str:
        """Extract searchable text from MemoryContent."""
        content = content_item.content

        if content_item.mime_type in [MimeType.TEXT, MimeType.MARKDOWN]:
            return str(content)
        elif content_item.mime_type == MimeType.JSON:
            if isinstance(content, dict):
                return str(content)
            raise ValueError("JSON content must be a dict")
        elif isinstance(content, Image):
            raise ValueError("Image content cannot be converted to text")
        else:
            raise ValueError(f"Unsupported content type: {content_item.mime_type}")

    async def transform(
        self,
        model_context: ChatCompletionContext,
    ) -> ChatCompletionContext:
        """Transform the model context using relevant memory content."""
        messages = await model_context.get_messages()
        if not messages:
            return model_context

        last_message = messages[-1]
        query_text = getattr(last_message, "content", str(last_message))
        query = MemoryContent(content=query_text, mime_type=MimeType.TEXT)

        results = []
        query_results = await self.query(query)
        for i, result in enumerate(query_results, 1):
            results.append(f"{i}. {result.entry.content.content}")

        if results:
            memory_context = "Results from memory query to consider include:\n" + "\n".join(results)
            await model_context.add_message(SystemMessage(content=memory_context))

        return model_context

    async def add(self, entry: MemoryEntry, cancellation_token: CancellationToken | None = None) -> None:
        """Add a memory entry to ChromaDB."""
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            # Extract text from MemoryContent
            text = self._extract_text(entry.content)

            # Prepare metadata
            metadata: ChromaMetadata = {
                "timestamp": entry.timestamp.isoformat(),
                "source": entry.source or "",
                "mime_type": entry.content.mime_type.value,
                **entry.metadata,
            }

            # Add to ChromaDB
            self._collection.add(documents=[text], metadatas=[metadata], ids=[str(uuid.uuid4())])

        except Exception as e:
            logger.error(f"Failed to add entry to ChromaDB: {e}")
            raise

    async def query(
        self,
        query: MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> List[MemoryQueryResult]:
        """Query memory entries based on vector similarity."""
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            # Extract text for query
            query_text = self._extract_text(query)

            # Query ChromaDB
            results = self._collection.query(query_texts=[query_text], n_results=self._config.k, **kwargs)

            # Convert results to MemoryQueryResults
            memory_results: List[MemoryQueryResult] = []

            if not results["documents"]:
                return memory_results

            for doc, metadata, distance in zip(
                results["documents"][0], results["metadatas"][0], results["distances"][0]
            ):
                # Extract stored metadata
                entry_metadata = dict(metadata)
                timestamp_str = str(entry_metadata.pop("timestamp"))
                timestamp = datetime.fromisoformat(timestamp_str)
                source = str(entry_metadata.pop("source"))
                mime_type = MimeType(entry_metadata.pop("mime_type"))

                # Create MemoryContent and MemoryEntry
                content_item = MemoryContent(content=doc, mime_type=mime_type)
                entry = MemoryEntry(
                    content=content_item, metadata=entry_metadata, timestamp=timestamp, source=source or None
                )

                # Convert distance to similarity score
                score = (
                    1.0 - (float(distance) / 2.0)
                    if self._config.distance_metric == "cosine"
                    else 1.0 / (1.0 + float(distance))
                )

                # Apply score threshold if configured
                if self._config.score_threshold is None or score >= self._config.score_threshold:
                    memory_results.append(MemoryQueryResult(entry=entry, score=score))

            return memory_results

        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            raise

    async def clear(self) -> None:
        """Clear all entries from memory."""
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            self._collection.delete()
            if self._client is not None:
                self._collection = self._client.get_or_create_collection(
                    name=self._config.collection_name, metadata={"distance_metric": self._config.distance_metric}
                )
        except Exception as e:
            logger.error(f"Failed to clear ChromaDB collection: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up ChromaDB client."""
        if self._client is not None:
            try:
                if hasattr(self._client, "reset"):
                    self._client.reset()
            except Exception as e:
                logger.error(f"Error during ChromaDB cleanup: {e}")
            finally:
                self._client = None
                self._collection = None
