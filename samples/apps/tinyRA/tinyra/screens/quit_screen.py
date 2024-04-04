from textual import on
from textual.app import ComposeResult
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class QuitScreen(ModalScreen):
    """Screen with a dialog to quit."""

    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    CSS_PATH = "quit_screen.css"

    def compose(self) -> ComposeResult:
        with Grid(id="quit-screen-grid"):
            yield Label("Are you sure you want to quit?", id="quit-question", classes="heading")
            with Grid(id="quit-screen-footer"):
                yield Button("Quit", variant="error", id="quit")
                yield Button("Cancel", variant="primary", id="cancel")

    @on(Button.Pressed, "#quit")
    def quit(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(False)
