from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import TabbedContent, Label
from textual.containers import Grid, Container, ScrollableContainer

from .profiler_screen import ProfilerContainer
from .chat_display import ChatDisplay
from .learning.learning import LearningTab


class MonitoringScreen(ModalScreen):
    """A screen that displays a chat history"""

    DEFAULT_CSS = """

    MonitoringScreen {
        align: center middle;
    }

    #monitoring {
        height: 90%;
        width: 90%;

        background: $surface;
        border: thick $primary-background 80%;

        layout: grid;
        grid-size: 1 2;
        grid-rows: 3 1fr;
    }

    #monitoring-header {
        align: center middle;
    }

    #chat-screen-learning {
        padding: 0;
    }
    """

    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    def __init__(self, *args, root_id: int = -1, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_id = root_id

    def compose(self) -> ComposeResult:

        with Grid(id="monitoring"):

            with Container(id="monitoring-header"):
                yield Label(f"Monitoring Agents (Task-{self.root_id})", classes="heading")

            with TabbedContent("Overview", "Details", "Learning", id="chat-screen-tabs"):

                profiler = ProfilerContainer(id="chat-profiler", root_id=self.root_id)
                yield profiler

                with ScrollableContainer(id="chat-screen-contents"):
                    yield ChatDisplay(root_id=self.root_id)

                with ScrollableContainer(id="chat-screen-learning"):
                    yield LearningTab(root_id=self.root_id)
