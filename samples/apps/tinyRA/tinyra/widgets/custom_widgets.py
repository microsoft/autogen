from textual.app import ComposeResult
from textual.widgets import LoadingIndicator, Static, Label
from textual.containers import Grid


class Title(Static):

    CSS_FILE = "custom_widgets.css"

    pass


class NamedLoadingIndicator(Grid):

    DEFAULT_CSS = """
    NamedLoadingIndicator {
        height: 100%;
        width: 100%;

        grid-size: 1 2;
        grid-rows: 1 1;

        content-align: center middle;
    }

    NamedLoadingIndicator > Static {
        content-align: center bottom;
        width: 100%;
        height: 50%;
        dock: top;
        color: $accent;
    }

    NamedLoadingIndicator > LoadingIndicator {
        content-align: center top;
        width: 100%;
        height: 50%;
        dock: bottom;
    }
    """

    def __init__(self, *args, text: str, **kwargs):
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        yield Static(self.text)
        yield LoadingIndicator()


class PlaceholderStatic(Static):

    DEFAULT_CSS = """

    PlaceholderStatic {
        color: $accent;
        content-align: center middle;
        height: 100%;
    }

    """


# class DarkSwitch(Horizontal):
#     def compose(self) -> ComposeResult:
#         yield Switch(value=self.app.dark)
#         yield Static("Dark mode toggle", classes="label")

#     def on_mount(self) -> None:
#         self.watch(self.app, "dark", self.on_dark_change, init=False)

#     def on_dark_change(self) -> None:
#         self.query_one(Switch).value = self.app.dark

#     def on_switch_changed(self, event: Switch.Changed) -> None:
#         self.app.dark = event.value
