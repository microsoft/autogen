from typing import Optional

from textual.app import ComposeResult
from textual import on
from textual.widgets import Button, Static
from textual.containers import Grid
from textual.screen import ModalScreen


class NotificationScreen(ModalScreen):
    """Screen with a dialog to display notifications."""

    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    def __init__(self, *args, message: Optional[str] = None, **kwargs):
        self.message = message or ""
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        with Grid(id="notification-screen-grid"):
            yield Static(self.message, id="notification")

            with Grid(id="notification-screen-footer"):
                yield Button("Dismiss", variant="primary", id="dismiss-notification")

    @on(Button.Pressed, "#dismiss-notification")
    def dismiss(self) -> None:  # type: ignore[override]
        self.app.pop_screen()
