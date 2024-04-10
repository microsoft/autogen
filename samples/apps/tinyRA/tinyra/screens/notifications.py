from typing import Optional

from textual.app import ComposeResult
from textual import on
from textual.widgets import Button, Static
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen


class NotificationScreen(ModalScreen):
    """Screen with a dialog to display notifications."""

    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    DEFAULT_CSS = """

    NotificationScreen {
        align: center middle;
    }

    #notification-screen-grid {
        height: 40%;
        width: 40%;
        border: thick $primary 80%;
        padding: 1;

        layout: grid;
        grid-rows: 1fr 5;
    }

    #notification-text {
        text-style: bold;
        text-align: center;
        content-align: center middle;
    }

    #notification-screen-footer {
        align: center middle;
    }

    #notification-screen-footer Button{
        width: auto;
    }
    """

    def __init__(self, *args, message: Optional[str] = None, **kwargs):
        self.message = message or ""
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        with Vertical(id="notification-screen-grid"):

            yield Static(self.message, id="notification-text")

            with Grid(id="notification-screen-footer"):
                yield Button("Dismiss", variant="primary", id="dismiss-notification")

    @on(Button.Pressed, "#dismiss-notification")
    def dismiss(self) -> None:  # type: ignore[override]
        self.app.pop_screen()


class NotificationScreenSuccess(NotificationScreen):

    DEFAULT_CSS = """
    #notification-screen-grid {
        border: thick $success 80%;
    }
    """


class NotificationScreenError(NotificationScreen):

    DEFAULT_CSS = """
    #notification-screen-grid {
        border: thick $error 80%;
    }
    """
