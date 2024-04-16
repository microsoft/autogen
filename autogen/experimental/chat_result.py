from dataclasses import dataclass

from autogen.experimental.chat_history import ChatHistoryReadOnly
from autogen.experimental.termination import TerminationResult


@dataclass
class ChatResult:
    conversation: ChatHistoryReadOnly
    summary: str
    termination_result: TerminationResult
