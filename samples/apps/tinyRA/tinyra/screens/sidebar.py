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

    DEFAULT_CSS = """
    Sidebar {
        width: 40%;
        background: $panel;
        border: thick $primary-background 90%;
        transition: offset 500ms in_out_cubic;
        layer: overlay;
        margin: 1;
        padding: 1;

        grid-size: 1 2;
        grid-rows: 1fr 5;
        grid-gutter: 1 2;
    }

    Sidebar:focus-within {
        offset: 0 0 !important;
    }

    Sidebar.-hidden {
        offset-x: -100%;
    }

    Sidebar Static {
        background: $boost;
        color: $secondary;
        border-right: vkey $background;
        dock: top;
        text-align: center;
        text-style: bold;
    }

    #directory-tree-footer{
        grid-size: 2 1;
        align: center middle;
    }

    """

    def compose(self) -> ComposeResult:
        logger = logging.getLogger(__name__)
        logger.info("Composing the sidebar")

        yield Static("Work Directory")

        yield DirectoryTreeContainer(id="directory-tree")

        with Grid(id="directory-tree-footer"):
            yield Button("Delete", variant="error", id="delete-file-button")
            yield Button("Empty Work Dir", variant="error", id="empty-work-dir-button")

    # @on(Button.Pressed, "#empty-work-dir-button")
    # def empty_work_dir(self, event: Button.Pressed) -> None:
    #     work_dir = APP_CONFIG.get_workdir()
    #     for file in os.listdir(work_dir):
    #         file_path = os.path.join(work_dir, file)
    #         if os.path.isfile(file_path):
    #             os.remove(file_path)
    #         elif os.path.isdir(file_path):
    #             shutil.rmtree(file_path)

    # @on(Button.Pressed, "#delete-file-button")
    # def delete_file(self, event: Button.Pressed) -> None:
    #     dir_tree = self.query_one("#directory-tree > DirectoryTree", DirectoryTree)
    #     highlighted_node = dir_tree.cursor_node

    #     if highlighted_node is not None:
    #         dir_tree.action_cursor_up()
    #         if highlighted_node.data is not None:
    #             file_path = str(highlighted_node.data.path)
    #             APP_CONFIG.delete_file_or_dir(file_path)
