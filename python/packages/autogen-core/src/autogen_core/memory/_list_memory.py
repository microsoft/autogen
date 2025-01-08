from typing import Any, List

from ._base_memory import Memory, MemoryContent
from ..models import SystemMessage
from ..model_context import ChatCompletionContext
from .._cancellation_token import CancellationToken


class ListMemory(Memory):
    """Simple chronological list-based memory implementation.

    This memory implementation stores contents in a list and retrieves them in
    chronological order. It has an `update_context` method that updates model contexts by appending all stored
    memories, limited by the configured maximum number of memories.

    Example:
        ```python
        # Initialize memory with custom config
        memory = ListMemory(name="chat_history", config=ListMemoryConfig(max_memories=5))

        # Add memory content
        content = MemoryContent(content="User prefers formal language")
        await memory.add(content)

        # Update a model context with memory
        memory_contents = await memory.update_context(model_context)
        ```

    Attributes:
        name (str): Identifier for this memory instance
        config (ListMemoryConfig): Configuration controlling memory behavior
    """

    def __init__(self, name: str | None = None, max_memories: int = 5) -> None:
        self._name = name or "default_list_memory"
        self._max_memories = max_memories
        self._contents: List[MemoryContent] = []

    @property
    def name(self) -> str:
        return self._name

    async def update_context(
        self,
        model_context: ChatCompletionContext,
    ) -> List[MemoryContent]:
        """Update the model context by appending recent memory content.

        This method mutates the provided model_context by adding the most recent memories (as a :class:`SystemMessage`), up to the configured maximum number of memories.

        Args:
            model_context: The context to update. Will be mutated if memories exist.

        Returns:
            List[MemoryContent]: List of memories that were added to the context
        """
        if not self._contents:
            return []

        # Get the most recent memories up to max_memories
        recent_memories = self._contents[-self._max_memories:]

        # Format memories into a string
        memory_strings = []
        for i, memory in enumerate(recent_memories, 1):
            content = memory.content if isinstance(
                memory.content, str) else str(memory.content)
            memory_strings.append(f"{i}. {content}")

        # Add memories to context if there are any
        if memory_strings:
            memory_context = (
                "\nRelevant memory content (in chronological order):\n"
                + "\n".join(memory_strings)
                + "\n"
            )
            await model_context.add_message(SystemMessage(content=memory_context))

        return recent_memories

    async def query(
        self,
        query: MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> List[MemoryContent]:
        """Return most recent memories without any filtering.

        Args:
            query: Ignored in this implementation
            cancellation_token: Optional token to cancel operation
            **kwargs: Additional parameters (ignored)

        Returns:
            List[MemoryContent]: Most recent memories up to max_memories limit
        """
        _ = query
        return self._contents[-self._max_memories:]

    async def add(
        self,
        content: MemoryContent,
        cancellation_token: CancellationToken | None = None
    ) -> None:
        """Add new content to memory.

        Args:
            content: Memory content to store
            cancellation_token: Optional token to cancel operation
        """
        self._contents.append(content)

    async def clear(self) -> None:
        """Clear all memory content."""
        self._contents = []

    async def close(self) -> None:
        """Cleanup resources if needed."""
        pass
