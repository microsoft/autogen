from textual.message import Message
from .database.database import ChatMessage


class SelectedReactiveMessage(Message):
    """The user click on a reactive message widget."""

    def __init__(self, message: ChatMessage) -> None:
        self.message = message
        super().__init__()


class UserNotification(Message):
    """A general notification message for the app."""

    status: str = "info"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()


class UserNotificationSuccess(UserNotification):
    """A success notification message for the app."""

    status: str = "success"


class UserNotificationError(UserNotification):
    """An error message for the app."""

    status: str = "error"
