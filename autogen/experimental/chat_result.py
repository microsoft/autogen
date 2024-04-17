from dataclasses import dataclass

from .chat_history import ChatHistoryReadOnly
from .termination import TerminationResult


@dataclass
class ChatResult:
    conversation: ChatHistoryReadOnly
    summary: str
    termination_result: TerminationResult
