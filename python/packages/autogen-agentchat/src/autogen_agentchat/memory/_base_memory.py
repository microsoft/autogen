from datetime import datetime
from typing import Any, Dict, List, Protocol, Union, runtime_checkable

from autogen_core.base import CancellationToken
from autogen_core.components import Image
from pydantic import BaseModel, ConfigDict, Field


class BaseMemoryConfig(BaseModel):
    """Base configuration for memory implementations."""

    k: int = Field(default=5, description="Number of results to return")
    score_threshold: float | None = Field(default=None, description="Minimum relevance score")
    context_format: str = Field(
        default="Context {i}: {content} (score: {score:.2f})\n Use this information to address relevant tasks.",
        description="Format string for memory results in prompt",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MemoryEntry(BaseModel):
    """A memory entry containing content and metadata."""

    content: Union[str, List[Union[str, Image]]]
    """The content of the memory entry - can be text or multimodal."""

    metadata: Dict[str, Any] = Field(default_factory=dict)
    """Optional metadata associated with the memory entry."""

    timestamp: datetime = Field(default_factory=datetime.now)
    """When the memory was created."""

    source: str | None = None
    """Optional source identifier for the memory."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MemoryQueryResult(BaseModel):
    """Result from a memory query including the entry and its relevance score."""

    entry: MemoryEntry
    """The memory entry."""

    score: float
    """Relevance score for this result. Higher means more relevant."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


@runtime_checkable
class Memory(Protocol):
    """Protocol defining the interface for memory implementations."""

    @property
    def name(self) -> str | None:
        """The name of this memory implementation."""
        ...

    @property
    def config(self) -> BaseMemoryConfig:
        """The configuration for this memory implementation."""
        ...

    async def query(
        self,
        query: Union[str, Image, List[Union[str, Image]]],
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> List[MemoryQueryResult]:
        """
        Query the memory store and return relevant entries.

        Args:
            query: Text, image or multimodal query
            cancellation_token: Optional token to cancel operation
            **kwargs: Additional implementation-specific parameters

        Returns:
            List of memory entries with relevance scores
        """
        ...

    async def add(self, entry: MemoryEntry, cancellation_token: CancellationToken | None = None) -> None:
        """
        Add a new entry to memory.

        Args:
            entry: The memory entry to add
            cancellation_token: Optional token to cancel operation
        """
        ...

    async def clear(self) -> None:
        """Clear all entries from memory."""
        ...

    async def cleanup(self) -> None:
        """Clean up any resources used by the memory implementation."""
        ...
