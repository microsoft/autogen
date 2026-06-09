from typing import TYPE_CHECKING, Any

from autogen_core import CancellationToken, Image
from autogen_core.memory import Memory, MemoryContent, MemoryMimeType, MemoryQueryResult, UpdateContextResult
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import UserMessage

if TYPE_CHECKING:
    from autogen_ext.experimental.task_centric_memory import MemoryController


class Teachability(Memory):
    """
    Gives an AssistantAgent the ability to learn quickly from user teachings, hints, and advice.

    Steps for usage:

        1. Instantiate MemoryController.
        2. Instantiate Teachability, passing the memory controller as a parameter.
        3. Instantiate an AssistantAgent, passing the teachability instance (wrapped in a list) as the memory parameter.
        4. Use the AssistantAgent as usual, such as for chatting with the user.
    """

    def __init__(self, memory_controller: "MemoryController", name: str | None = None) -> None:
        """Initialize Teachability."""
        self._memory_controller = memory_controller
        self._logger = memory_controller.logger
        self._name = name or "teachability"

    @property
    def name(self) -> str:
        """Get the memory instance identifier."""
        return self._name

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

    async def update_context(
        self,
        model_context: ChatCompletionContext,
    ) -> UpdateContextResult:
        """
        Extracts any advice from the last user turn to be stored in memory,
        and adds any relevant memories to the model context.
        """
        self._logger.enter_function()

        # Extract text from the user's last message
        messages = await model_context.get_messages()
        if not messages:
            self._logger.leave_function()
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))
        last_message = messages[-1]
        last_user_text = last_message.content if isinstance(last_message.content, str) else str(last_message)

        # Add any relevant memories to the chat history
        query_results = await self.query(last_user_text)
        if query_results.results:
            memory_strings = [f"{i}. {str(memory.content)}" for i, memory in enumerate(query_results.results, 1)]
            memory_context = "\nPotentially relevant memories:\n" + "\n".join(memory_strings)
            await model_context.add_message(UserMessage(content=memory_context, source="user"))

        # Add any user advice to memory
        await self._memory_controller.consider_memo_storage(last_user_text)

        self._logger.leave_function()
        return UpdateContextResult(memories=query_results)

    async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
        """
        Tries to extract any advice from the passed content and add it to memory.
        """
        self._logger.enter_function()

        # Extract text from the incoming content
        text = self._extract_text(content)

        # Check for advice to add to memory for later turns.
        await self._memory_controller.consider_memo_storage(text)

        self._logger.leave_function()

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """
        Returns any memories that seem relevant to the query.
        """
        self._logger.enter_function()

        task = self._extract_text(query)
        memory_results: list[MemoryContent] = []
        filtered_memos = await self._memory_controller.retrieve_relevant_memos(task=task)
        filtered_insights = [memo.insight for memo in filtered_memos]
        for insight in filtered_insights:
            self._logger.info(f"Insight: {insight}")
            memory_content = MemoryContent(
                content=insight,
                mime_type="MemoryMimeType.TEXT",
                metadata={},
            )
            memory_results.append(memory_content)

        self._logger.leave_function()
        return MemoryQueryResult(results=memory_results)

    async def clear(self) -> None:
        """Clear all entries from memory."""
        self._memory_controller.reset_memory()

    async def close(self) -> None:
        """Clean up memory resources."""
        pass  # No cleanup needed for this memory implementation
