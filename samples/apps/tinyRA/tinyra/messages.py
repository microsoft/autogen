from textual.message import Message


class AppErrorMessage(Message):
    """An error message for the app."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()
