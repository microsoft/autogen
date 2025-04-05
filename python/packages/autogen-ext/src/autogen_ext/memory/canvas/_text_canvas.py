# file: canvas_memory.py

from autogen_core.memory import (
    Memory,
    MemoryContent,
    MemoryQueryResult,
    UpdateContextResult,
    MemoryMimeType,
)
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage

from typing import Any
from ._canvas import Canvas


class TextCanvasMemory(Memory):
    """
    A memory implementation that uses a Canvas for storing file-like content.
    Inserts the current state of the canvas into the ChatCompletionContext on each turn
    (or you could also insert diffs, etc.)
    """

    def __init__(self, canvas: Canvas):
        super().__init__()
        self.canvas = canvas

    async def update_context(self, model_context: ChatCompletionContext) -> UpdateContextResult:
        """
        Inject the entire canvas summary (or a selected subset) as reference data.
        Here, we just put it into a system message, but you could customize.
        """
        snapshot = self.canvas.get_all_contents_for_context()
        if snapshot.strip():
            msg = SystemMessage(content=snapshot)
            await model_context.add_message(msg)

            # Return it for debugging/logging
            memory_content = MemoryContent(content=snapshot, mime_type=MemoryMimeType.TEXT)
            return UpdateContextResult(memories=MemoryQueryResult(results=[memory_content]))

        return UpdateContextResult(memories=MemoryQueryResult(results=[]))

    async def query(self, query: str | MemoryContent, cancellation_token=None, **kwargs: Any) -> MemoryQueryResult:
        """
        Potentially search for matching filenames or file content.
        This example returns empty.
        """
        return MemoryQueryResult(results=[])

    async def add(self, content: MemoryContent, cancellation_token=None) -> None:
        """
        Example usage: Possibly interpret content as a patch or direct file update.
        Could also be done by a specialized "CanvasTool" instead.
        """
        # NO-OP here, leaving actual changes to the CanvasTool
        pass

    async def clear(self) -> None:
        # If you want to clear the entire canvas:
        self.canvas.__init__()  # naive: re-init
        pass

    async def close(self) -> None:
        pass
