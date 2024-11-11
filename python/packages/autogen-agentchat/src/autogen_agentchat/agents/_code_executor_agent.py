from typing import List, Sequence

from autogen_core.base import CancellationToken
from autogen_core.components.code_executor import CodeBlock, CodeExecutor, extract_markdown_code_blocks

from ..base import Response
from ..messages import ChatMessage, TextMessage
from ._base_chat_agent import BaseChatAgent


class CodeExecutorAgent(BaseChatAgent):
    """An agent that executes code snippets and report the results."""

    def __init__(
        self,
        name: str,
        code_executor: CodeExecutor,
        *,
        description: str = "A computer terminal that performs no other action than running Python scripts (provided to it quoted in ```python code blocks), or sh shell scripts (provided to it quoted in ```sh code blocks).",
    ) -> None:
        super().__init__(name=name, description=description)
        self._code_executor = code_executor

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        """The types of messages that the code executor agent produces."""
        return [TextMessage]

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        # Extract code blocks from the messages.
        code_blocks: List[CodeBlock] = []
        for msg in messages:
            if isinstance(msg, TextMessage):
                code_blocks.extend(extract_markdown_code_blocks(msg.content))
        if code_blocks:
            # Execute the code blocks.
            result = await self._code_executor.execute_code_blocks(code_blocks, cancellation_token=cancellation_token)
            return Response(chat_message=TextMessage(content=result.output, source=self.name))
        else:
            return Response(chat_message=TextMessage(content="No code blocks found in the thread.", source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """It it's a no-op as the code executor agent has no mutable state."""
        pass
