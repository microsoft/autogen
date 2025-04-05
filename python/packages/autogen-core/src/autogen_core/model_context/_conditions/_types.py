from typing import Literal


class TriggerMessage:
    """A message requesting trigger of a completion context."""

    type: Literal["TriggerMessage"] = "TriggerMessage"
    content: str

    def __init__(self, content: str) -> None:
        self.content = content
