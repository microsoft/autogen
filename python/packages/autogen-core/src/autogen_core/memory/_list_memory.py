from typing import Any, List

from .._cancellation_token import CancellationToken
from ..model_context import ChatCompletionContext
from ..models import SystemMessage
from ._base_memory import Memory, MemoryContent, MemoryQueryResult, UpdateContextResult


class ListMemory(Memory):
    """Simple chronological list-based memory implementation.

    This memory implementation stores contents in a list and retrieves them in
    chronological order. It has an `update_context` method that updates model contexts
    by appending all stored memories.

    The memory content can be directly accessed and modified through the content property,
    allowing external applications to manage memory contents directly.

    Example:
         .. code-block:: python
             # Initialize memory
             memory = ListMemory(name="chat_history")

             # Add memory content
             content = MemoryContent(content="User prefers formal language")
             await memory.add(content)

             # Directly modify memory contents
             memory.content = [MemoryContent(content="New preference")]

             # Update a model context with memory
             memory_contents = await memory.update_context(model_context)


    Attributes:
        name (str): Identifier for this memory instance
        content (List[MemoryContent]): Direct access to memory contents
    """

    def __init__(self, name: str | None = None) -> None:
        """Initialize ListMemory.

        Args:
            name: Optional identifier for this memory instance
        """
        self._name = name or "default_list_memory"
        self._contents: List[MemoryContent] = []

    @property
    def name(self) -> str:
        """Get the memory instance identifier.

        Returns:
            str: Memory instance name
        """
        return self._name

    @property
    def content(self) -> List[MemoryContent]:
        """Get the current memory contents.

        Returns:
            List[MemoryContent]: List of stored memory contents
        """
        return self._contents

    @content.setter
    def content(self, value: List[MemoryContent]) -> None:
        """Set the memory contents.

        Args:
            value: New list of memory contents to store
        """
        self._contents = value

    async def update_context(
        self,
        model_context: ChatCompletionContext,
    ) -> UpdateContextResult:
        """Update the model context by appending memory content.

        This method mutates the provided model_context by adding all memories as a
        SystemMessage.

        Args:
            model_context: The context to update. Will be mutated if memories exist.

        Returns:
            UpdateContextResult containing the memories that were added to the context
        """

        if not self._contents:
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))

        memory_strings = [f"{i}. {str(memory.content)}" for i, memory in enumerate(self._contents, 1)]

        if memory_strings:
            memory_context = "\nRelevant memory content (in chronological order):\n" + "\n".join(memory_strings) + "\n"
            await model_context.add_message(SystemMessage(content=memory_context))

        return UpdateContextResult(memories=MemoryQueryResult(results=self._contents))

    async def query(
        self,
        query: str | MemoryContent = "",
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """Return all memories without any filtering.

        Args:
            query: Ignored in this implementation
            cancellation_token: Optional token to cancel operation
            **kwargs: Additional parameters (ignored)

        Returns:
            MemoryQueryResult containing all stored memories
        """
        _ = query, cancellation_token, kwargs
        return MemoryQueryResult(results=self._contents)

    async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
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
