import logging
import uuid
from typing import Any, Dict

from autogen_core import CancellationToken, Image
from autogen_core.memory import Memory, MemoryContent, MemoryMimeType, MemoryQueryResult, UpdateContextResult
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage
from chromadb import Client, PersistentClient
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class ChromaMemoryContent(MemoryContent):
    """Memory content with additional ChromaDB-specific fields."""
    
    score: float | None = None
    """Similarity score from vector search"""


class ChromaMemoryConfig(BaseModel):
    """Configuration for ChromaDB-based memory implementation."""

    collection_name: str = Field(default="memory_store", description="Name of the ChromaDB collection")
    persistence_path: str | None = Field(default=None, description="Path for persistent storage. None for in-memory.")
    distance_metric: str = Field(default="cosine", description="Distance metric for similarity search")
    k: int = Field(default=5, description="Number of results to return in queries")
    score_threshold: float | None = Field(default=None, description="Minimum similarity score threshold")
    allow_reset: bool = Field(default=False, description="Whether to allow resetting the ChromaDB client")


class ChromaMemory(Memory):
    """ChromaDB-based vector memory implementation with similarity search."""

    def __init__(self, name: str | None = None, config: ChromaMemoryConfig | None = None) -> None:
        """Initialize ChromaMemory."""
        self._name = name or "default_chroma_memory"
        self._config = config or ChromaMemoryConfig()
        self._client: ClientAPI | None = None
        self._collection: Collection | None = None

    @property
    def name(self) -> str:
        """Get the memory instance identifier."""
        return self._name

    def _ensure_initialized(self) -> None:
        """Ensure ChromaDB client and collection are initialized."""
        if self._client is None:
            try:
                from chromadb.config import Settings

                settings = Settings(allow_reset=self._config.allow_reset)

                self._client = (
                    PersistentClient(path=self._config.persistence_path, settings=settings)
                    if self._config.persistence_path
                    else Client(settings=settings)
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
        """Update the model context with relevant memory content."""
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

            # Convert results to ChromaMemoryContent list
            memory_results: list[ChromaMemoryContent] = []

            if (
                not results
                or not results.get("documents")
                or not results.get("metadatas")
                or not results.get("distances")
            ):
                return MemoryQueryResult(results=memory_results)

            documents = results["documents"][0] if results["documents"] else []
            metadatas = results["metadatas"][0] if results["metadatas"] else []
            distances = results["distances"][0] if results["distances"] else []

            for doc, metadata_dict, distance in zip(documents, metadatas, distances, strict=False):
                # Calculate score
                score = self._calculate_score(distance)

                if self._config.score_threshold is not None and score < self._config.score_threshold:
                    continue

                # Extract mime_type from metadata
                mime_type = metadata_dict.pop("mime_type")
                
                # Create ChromaMemoryContent
                content = ChromaMemoryContent(
                    content=doc,
                    mime_type=mime_type,
                    metadata=metadata_dict,
                    score=score
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