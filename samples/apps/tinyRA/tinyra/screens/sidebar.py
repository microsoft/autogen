import logging
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.widgets import DirectoryTree, Button, Static

from ..widgets.custom_widgets import Title
from ..exceptions import FileManagerError


class DirectoryTreeContainer(Container):
    """
    A container for displaying the directory tree.
    """

    dir_contents = reactive("")

    def compose(self) -> ComposeResult:
        fm = self.app.config.file_manager
        dirpath = fm.get_root_path()
        yield DirectoryTree(dirpath)

    def on_mount(self) -> None:
        self.set_interval(1, self.update_dir_contents)

    def update_dir_contents(self) -> None:
        fm = self.app.config.file_manager
        self.dir_contents = str(fm.list_files())

    def watch_dir_contents(self):
        self.query_one(DirectoryTree).reload()

    def on_tree_node_highlighted(self, event: DirectoryTree.NodeHighlighted) -> None:
        self.highlighted_node = event.node

    async def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Called when the user click a file in the directory tree."""
        logger = logging.getLogger(__name__)
        logger.info(f"File selected: {event.path}")
        event.stop()
        try:
            fm = self.app.config.file_manager
            logger.info(f"Opening file {event.path}")
            await fm.open_file(event.path)
        except Exception as e:
            raise FileManagerError(f"Error opening file {event.path}", e)


class Sidebar(Grid):

    def compose(self) -> ComposeResult:
        logger = logging.getLogger(__name__)
        logger.info("Composing the sidebar")

        yield Static("Work Directory")

        yield DirectoryTreeContainer(id="directory-tree")

        with Grid(id="directory-tree-footer"):
            yield Button("Delete", variant="error", id="delete-file-button")
            yield Button("Empty Work Dir", variant="error", id="empty-work-dir-button")
