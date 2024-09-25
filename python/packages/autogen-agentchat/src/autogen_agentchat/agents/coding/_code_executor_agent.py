from typing import List, Sequence

from autogen_core.base import CancellationToken
from autogen_core.components.code_executor import CodeBlock, CodeExecutor, extract_markdown_code_blocks
from autogen_core.components.models import UserMessage

from .._base_chat_agent import BaseChatAgent, ChatMessage


class CodeExecutorAgent(BaseChatAgent):
    """An agent that executes code snippets and report the results."""

    DESCRIPTION = "A computer terminal that performs no other action than running Python scripts (provided to it quoted in ```python code blocks), or sh shell scripts (provided to it quoted in ```sh code blocks)."

    def __init__(self, name: str, code_executor: CodeExecutor):
        """Initialize the agent with a code executor."""
        super().__init__(name=name, description=self.DESCRIPTION)
        self._code_executor = code_executor

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> ChatMessage:
        # Extract code blocks from the messages.
        code_blocks: List[CodeBlock] = []
        for msg in messages:
            if isinstance(msg.content, UserMessage) and isinstance(msg.content.content, str):
                code_blocks.extend(extract_markdown_code_blocks(msg.content.content))
        if code_blocks:
            # Execute the code blocks.
            result = await self._code_executor.execute_code_blocks(code_blocks, cancellation_token=cancellation_token)
            return ChatMessage(content=UserMessage(content=result.output, source=self.name), request_pause=False)
        else:
            return ChatMessage(
                content=UserMessage(content="No code blocks found in the thread.", source=self.name),
                request_pause=False,
            )
