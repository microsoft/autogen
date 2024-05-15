from typing import Protocol


class Message(Protocol):
    sender: str
    # reply_to: Optional[str]
