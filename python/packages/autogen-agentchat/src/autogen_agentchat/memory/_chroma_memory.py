from typing import Any, List, Optional, Union, Dict
from types import TracebackType
from datetime import datetime
import chromadb
from chromadb.types import Collection
import uuid
import logging
from autogen_core.base import CancellationToken
from autogen_core.components import Image
from pydantic import Field

from ._base_memory import BaseMemoryConfig, Memory, MemoryEntry, MemoryQueryResult

logger = logging.getLogger(__name__)

# Type vars for ChromaDB results
ChromaMetadata = Dict[str, Union[str, float, int, bool]]
ChromaDistance = Union[float, List[float]]


class ChromaMemoryConfig(BaseMemoryConfig):
    """Configuration for ChromaDB-based memory implementation."""

    collection_name: str = Field(
        default="memory_store", description="Name of the ChromaDB collection")
    persistence_path: Optional[str] = Field(
        default=None, description="Path for persistent storage. None for in-memory."
    )
    distance_metric: str = Field(
        default="cosine", description="Distance metric for similarity search")


class ChromaMemory(Memory):
    """ChromaDB-based memory implementation using default embeddings."""

    def __init__(self, name: Optional[str] = None, config: Optional[ChromaMemoryConfig] = None) -> None:
        """Initialize ChromaMemory."""
        self._name = name or "default_chroma_memory"
        self._config = config or ChromaMemoryConfig()
        self._client: Optional[chromadb.Client] = None  # type: ignore
        self._collection: Collection | None = None  # type: ignore

    @property
    def name(self) -> Optional[str]:
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
                    name=self._config.collection_name, metadata={
                        "distance_metric": self._config.distance_metric}
                )
            except Exception as e:
                logger.error(f"Failed to get/create collection: {e}")
                raise

    def _extract_text(self, content: Union[str, List[Union[str, Image]]]) -> str:
        """Extract text content from input."""
        if isinstance(content, str):
            return content

        text_parts = [item for item in content if isinstance(item, str)]
        if not text_parts:
            raise ValueError("Content must contain at least one text element")

        return " ".join(text_parts)

    async def add(self, entry: MemoryEntry, cancellation_token: Optional[CancellationToken] = None) -> None:
        """Add a memory entry to ChromaDB."""
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            # Extract text
            text = self._extract_text(entry.content)

            # Prepare metadata
            metadata: ChromaMetadata = {
                "timestamp": entry.timestamp.isoformat(),
                "source": entry.source or "",
                **entry.metadata,
            }

            # Add to ChromaDB
            self._collection.add(documents=[text], metadatas=[
                                 metadata], ids=[str(uuid.uuid4())])

        except Exception as e:
            logger.error(f"Failed to add entry to ChromaDB: {e}")
            raise

    async def query(
        self,
        query: Union[str, Image, List[Union[str, Image]]],
        cancellation_token: Optional[CancellationToken] = None,
        **kwargs: Any,
    ) -> List[MemoryQueryResult]:
        """Query memory entries based on vector similarity."""
        self._ensure_initialized()
        if self._collection is None:
            raise RuntimeError("Failed to initialize ChromaDB")

        try:
            # Extract text for query
            if isinstance(query, Image):
                raise ValueError("Image-only queries are not supported")

            query_text = self._extract_text(
                query if isinstance(query, list) else [query])

            # Query ChromaDB
            results = self._collection.query(
                query_texts=[query_text], n_results=self._config.k, **kwargs)

            # Convert results to MemoryQueryResults
            memory_results: List[MemoryQueryResult] = []

            if not results["documents"]:
                return memory_results

            for doc, metadata, distance in zip(
                results["documents"][0], results["metadatas"][0], results["distances"][0]
            ):
                # Extract stored metadata
                entry_metadata = dict(metadata)
                try:
                    timestamp_str = str(entry_metadata.pop("timestamp"))
                    timestamp = datetime.fromisoformat(timestamp_str)
                except (KeyError, ValueError) as e:
                    logger.error(f"Invalid timestamp in metadata: {e}")
                    continue

                source = str(entry_metadata.pop("source"))

                # Create MemoryEntry
                entry = MemoryEntry(
                    content=doc, metadata=entry_metadata, timestamp=timestamp, source=source or None)

                # Convert distance to similarity score (1 - normalized distance)
                score = (
                    1.0 - (float(distance) / 2.0)
                    if self._config.distance_metric == "cosine"
                    else 1.0 / (1.0 + float(distance))
                )

                memory_results.append(
                    MemoryQueryResult(entry=entry, score=score))

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
                    name=self._config.collection_name, metadata={
                        "distance_metric": self._config.distance_metric}
                )
        except Exception as e:
            logger.error(f"Failed to clear ChromaDB collection: {e}")
            raise

    async def __aenter__(self) -> "ChromaMemory":
        """Context manager entry."""
        return self

    async def __aexit__(
        self, exc_type: Optional[type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        """Context manager exit with cleanup."""
        await self.cleanup()

    async def cleanup(self) -> None:
        """Clean up ChromaDB client."""
        if self._client is not None:
            try:
                if hasattr(self._client, "reset"):
                    self._client.reset()
                self._client = None
                self._collection = None
            except Exception as e:
                logger.error(f"Error during ChromaDB cleanup: {e}")
                # Maybe don't raise here, just log the error
                self._client = None
                self._collection = None
