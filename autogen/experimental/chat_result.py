from dataclasses import dataclass

from .chat_history import ChatHistoryReadOnly
from .termination import Terminated


@dataclass
class ChatResult:
    conversation: ChatHistoryReadOnly
    summary: str
    termination_result: Terminated
