from textual.message import Message
from .database.database import ChatMessage


class AppErrorMessage(Message):
    """An error message for the app."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()


class SelectedReactiveMessage(Message):
    """The user click on a reactive message widget."""

    def __init__(self, message: ChatMessage) -> None:
        self.message = message
        super().__init__()
