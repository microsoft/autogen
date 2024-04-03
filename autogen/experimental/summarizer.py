from typing import Protocol, Sequence

from .termination import TerminationResult

from .types import ChatMessage


class ChatSummarizer(Protocol):
    async def summarize_chat(self, messages: Sequence[ChatMessage], termination_result: TerminationResult) -> str: ...
