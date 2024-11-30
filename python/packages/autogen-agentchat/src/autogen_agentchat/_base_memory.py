from datetime import datetime
from typing import Any, Dict, List, Protocol, Union, runtime_checkable

from autogen_core.base import CancellationToken
from autogen_core.components import Image
from pydantic import BaseModel, ConfigDict, Field

from .state import BaseState


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


class BaseMemoryState(BaseState):
    """State for memory implementations."""

    state_type: str
    """Type identifier for the memory implementation."""

    entries: List[MemoryEntry]
    """List of memory entries."""


@runtime_checkable
class Memory(Protocol):
    """Protocol defining the interface for memory implementations."""

    @property
    def name(self) -> str:
        """The name of this memory implementation."""
        ...

    async def query(
        self,
        query: Union[str, Image, List[Union[str, Image]]],
        *,
        k: int = 5,
        score_threshold: float | None = None,
        **kwargs: Any
    ) -> List[MemoryQueryResult]:
        """
        Query the memory store and return relevant entries.

        Args:
            query: Text, image or multimodal query
            k: Maximum number of results to return
            score_threshold: Minimum relevance score threshold
            **kwargs: Additional implementation-specific parameters

        Returns:
            List of memory entries with relevance scores
        """
        ...

    async def add(
        self,
        entry: MemoryEntry,
        cancellation_token: CancellationToken | None = None
    ) -> None:
        """
        Add a new entry to memory.

        Args:
            entry: The memory entry to add
            cancellation_token: Optional token to cancel the operation
        """
        ...

    async def clear(self) -> None:
        """Clear all entries from memory."""
        ...

    async def save_state(self) -> BaseMemoryState:
        """Save memory state for persistence."""
        ...

    async def load_state(self, state: BaseState) -> None:
        """Load memory state from saved state."""
        ...


class BaseMemory:
    """Base class providing common functionality for memory implementations."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._entries: List[MemoryEntry] = []

    @property
    def name(self) -> str:
        return self._name

    async def clear(self) -> None:
        """Clear all entries from memory."""
        self._entries = []

    async def save_state(self) -> BaseMemoryState:
        """Save memory state."""
        return BaseMemoryState(
            state_type=self.__class__.__name__,
            entries=self._entries.copy()
        )

    async def load_state(self, state: BaseState) -> None:
        """Load memory state."""
        if not isinstance(state, BaseMemoryState):
            raise ValueError(f"Expected BaseMemoryState, got {type(state)}")

        if state.state_type != self.__class__.__name__:
            raise ValueError(
                f"Cannot load {state.state_type} state into {self.__class__.__name__}")

        self._entries = state.entries.copy()
