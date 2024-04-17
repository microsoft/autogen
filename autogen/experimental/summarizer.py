from typing import Protocol

from .chat_history import ChatHistoryReadOnly
from .termination import TerminationResult


class ChatSummarizer(Protocol):
    async def summarize_chat(self, chat_history: ChatHistoryReadOnly, termination_result: TerminationResult) -> str: ...
