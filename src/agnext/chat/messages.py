from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ChatMessage:
    """The message type for the chat API."""

    body: str
    sender: str
    save_message_only: bool = False
    payload: Optional[Any] = None
    reset: bool = False
