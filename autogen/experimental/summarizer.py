from typing import Protocol, Sequence

from .termination import TerminationResult
from .types import MessageAndSender


class ChatSummarizer(Protocol):
    async def summarize_chat(
        self, messages: Sequence[MessageAndSender], termination_result: TerminationResult
    ) -> str: ...
