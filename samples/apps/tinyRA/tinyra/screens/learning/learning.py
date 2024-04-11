from textual.app import ComposeResult
from textual.containers import Grid
from textual.widgets import TabbedContent, Markdown

from ...widgets.custom_widgets import NamedLoadingIndicator
from .tool_learning import ToolLearningWidget
from .preference_learning import PrefLearningWidget


class LearningTab(Grid):

    DEFAULT_CSS = """
    #learning-tabs {
        content-align: center middle;
        padding: 0;
        margin: 0;
        grid-size: 1 1;
    }
    """

    history = None

    def __init__(self, *args, root_id: int = -1, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_msg_id = root_id

    async def on_mount(self) -> None:
        history = await self.app.config.db_manager.get_chat_history(self.root_msg_id)
        self.history = history
        await self.recompose()

    def compose(self) -> ComposeResult:

        if self.history is None:
            yield NamedLoadingIndicator(text="Loading learning tools...")
            return

        with TabbedContent("Tools", "Preferences", id="learning-tabs"):
            yield ToolLearningWidget(history=self.history, app_config=self.app.config)
            yield PrefLearningWidget(history=self.history, app_config=self.app.config)
