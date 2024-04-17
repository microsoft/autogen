from typing import Protocol

from .chat_history import ChatHistoryReadOnly
from .termination import Terminated


class ChatSummarizer(Protocol):
    async def summarize_chat(self, chat_history: ChatHistoryReadOnly, termination_result: Terminated) -> str: ...
