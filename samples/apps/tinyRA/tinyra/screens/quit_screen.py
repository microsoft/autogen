from textual import on
from textual.app import ComposeResult
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class QuitScreen(ModalScreen):
    """Screen with a dialog to quit."""

    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    DEFAULT_CSS = """

    QuitScreen {
        align: center middle;
    }

    #quit-screen-grid{
        height: 40%;
        width: 40%;
        background: $surface;
        border: thick $primary-background 80%;
        padding: 1;

        grid-size: 1 2;
        grid-rows: 1fr 4;
    }

    #quit-question {
        width: 100%;
        height: 100%;
        text-align: center;
    }

    #quit-screen-footer {
        align: center middle;
        grid-size: 2 1;
    }

    """

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
