from typing import List

from textual import on
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Grid, Container, Horizontal, Vertical
from textual.widgets import (
    Static,
    Markdown,
    Input,
    Label,
    Button,
    TabbedContent,
    ListView,
    ListItem,
    TextArea,
    LoadingIndicator,
)

from ..exceptions import ToolUpdateError, InvalidToolError
from ..database.database import User
from ..tools import Tool
from ..messages import UserNotificationError, UserNotificationSuccess
from ..widgets.custom_widgets import PlaceholderStatic


class UserSettingsTab(Grid):

    user = None

    async def on_mount(self) -> None:
        dbm = self.app.config.db_manager
        user = await dbm.get_user()
        self.app.logger.info(f"UserSettingsTab {user}")
        self.user = user
        await self.recompose()

    def compose(self) -> ComposeResult:

        if self.user is None:
            yield LoadingIndicator()
            return

        self.widget_user_name = Input(self.user.name)
        self.widget_user_bio = TextArea(self.user.bio, id="user-bio")
        self.widget_user_preferences = TextArea(self.user.preferences, id="user-preferences")

        with Grid(id="user-settings-contents"):
            yield Container(Label("Name", classes="form-label"), self.widget_user_name)
            with TabbedContent("Bio", "Preferences"):
                yield self.widget_user_bio
                yield self.widget_user_preferences

        with Horizontal(classes="settings-screen-footer"):
            yield Button("Save", variant="primary", id="save-user-settings")

    @on(Button.Pressed, "#save-user-settings")
    async def save_user_settings(self) -> None:
        new_user_name = self.widget_user_name.value
        new_user_bio = self.widget_user_bio.text
        new_user_preferences = self.widget_user_preferences.text

        dbm = self.app.config.db_manager
        updated_user = User(new_user_name, new_user_bio, new_user_preferences)
        await dbm.set_user(updated_user)

        self.screen.close_settings()


class ToolViewer(Grid):

    DEFAULT_CSS = """

    ToolViewer {
        grid-size: 1 3;
        grid-rows: 6 1fr 4;
        grid-gutter: 1 2;
        border-left: solid $primary-background;
    }

    ToolViewer > PlaceholderStatic {
        row-span: 3;
    }

    """

    tool: Tool = reactive(None, recompose=True)

    def compose(self) -> ComposeResult:
        if self.tool is None:
            yield PlaceholderStatic("Select a tool to view or edit its settings", classes="instructions")
            return

        with Horizontal():
            with Vertical():
                yield Label("Tool ID", classes="form-label")
                yield Input(value=str(self.tool.id), id="tool-id-input", disabled=True)

            with Vertical():
                yield Label("Tool Name (Display)", classes="form-label")
                yield Input(value=self.tool.name, id="tool-name-input")

        # code editor for the selected tool
        with Horizontal(id="tool-code-container"):
            yield TextArea.code_editor(self.tool.code, language="python", id="tool-code-textarea")

        # footer for the tool view
        with Horizontal(id="tool-view-footer-grid"):
            yield Button("Save", variant="primary", id="save-tool-settings")
            yield Button("Delete", variant="error", id="delete-tool-button")


class ToolSettingsTab(Grid):

    tools: List[Tool] = None
    selected_tool: Tool = None

    async def on_mount(self) -> None:
        dbm = self.app.config.db_manager
        tools = await dbm.get_tools()
        self.tools = tools
        await self.recompose()

    def compose(self) -> ComposeResult:
        if self.tools is None:
            yield LoadingIndicator()
            return

        tools = self.tools
        # list of tools
        with Container(id="tool-list-container"):
            yield ListView(
                *(ListItem(Label(tool.name), id=f"tool-{tool.id}") for tool in tools),
                id="tool-list",
            )
            yield Button("+", variant="primary", id="new-tool-button")

        # display the settings for the selected tool
        yield ToolViewer(id="tool-view-grid")

    @on(Button.Pressed, "#new-tool-button")
    async def create_new_tool(self) -> None:
        dbm = self.app.config.db_manager

        tools = await dbm.get_tools()
        max_id = max(tools.id for tools in tools) if tools else 0
        new_id = max_id + 1
        new_tool_name = f"tool-{new_id}"
        tool = Tool(name=new_tool_name, id=new_id)

        try:
            tool.validate_tool()
        except Exception as e:
            error_message = f"{e}"
            self.post_message(UserNotificationError(error_message))
            return

        try:
            await dbm.set_tool(tool)
            self.app.logger.info(f"Created new tool: {new_tool_name}")
        except Exception as e:
            error_message = f"{e}"
            self.post_message(UserNotificationError(error_message))
            return

        list_view_widget = self.query_one("#tool-list", ListView)
        new_list_item = ListItem(Label(new_tool_name), id=f"tool-{tool.id}")

        list_view_widget.append(new_list_item)
        num_items = len(list_view_widget)
        list_view_widget.index = num_items - 1
        list_view_widget.action_select_cursor()

    @on(Button.Pressed, "#delete-tool-button")
    async def delete_tool(self) -> None:
        dbm = self.app.config.db_manager

        # get the id of the selected tool
        tool_id_str = self.query_one("#tool-id-input", Input).value
        # check if its a valid int
        try:
            tool_id = int(tool_id_str)
        except ValueError:
            error_message = "Tool ID must be an integer"
            self.post_message(UserNotificationError(error_message))
            return

        # tool_id = int(self.query_one("#tool-id-input", Input).value)
        item = self.query_one(f"#tool-{tool_id}", ListItem)
        # delete the tool from the database
        try:
            await dbm.delete_tool(tool_id)
        except ToolUpdateError as e:
            error_message = f"{e}"
            self.post_message(UserNotificationError(error_message))
            return

        # remove the tool from the list view
        item.remove()

        list_view_widget = self.query_one("#tool-list", ListView)

        if len(list_view_widget) > 0:
            list_view_widget.action_cursor_up()
            list_view_widget.action_select_cursor()
        else:
            self.query_one("#tool-code-textarea", TextArea).text = ""
            self.query_one("#tool-name-input", Input).value = ""
            self.query_one("#tool-id-input", Input).value = ""

    @on(Button.Pressed, "#save-tool-settings")
    async def save_tool_settings(self) -> None:
        # get the id of the selected tool
        dbm = self.app.config.db_manager

        tool_id = int(self.query_one("#tool-id-input", Input).value)
        tool_name = self.query_one("#tool-name-input", Input).value
        tool_code = self.query_one("#tool-code-textarea", TextArea).text

        tool = Tool(name=tool_name, code=tool_code, id=tool_id)

        try:
            tool.validate_tool()
        except InvalidToolError as e:
            error_message = f"{e}"
            self.post_message(UserNotificationError(error_message))
            return

        try:
            await dbm.set_tool(tool)
        except ToolUpdateError as e:
            error_message = f"{e}"
            self.post_message(UserNotificationError(error_message))
            return
        else:
            self.app.logger.info(f"Updated tool: {tool_name}")
            self.post_message(UserNotificationSuccess(f"Successfully saved {tool_name}"))

        item_label = self.query_one(f"#tool-{tool_id} > Label", Label)
        item_label.update(tool_name)
        # self.screen.close_settings()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        tool_id = int(event.item.id[5:])
        self.app.logger.info(f"Selected tool id: {tool_id}")
        dbm = self.app.config.db_manager

        try:
            tool = await dbm.get_tool_with_id(tool_id)
        except Exception as e:
            error_message = f"{e}"
            self.post_message(UserNotificationError(error_message))
            return

        self.app.logger.info(f"Selected tool: {tool}")
        viewer_widget = self.query_one("#tool-view-grid", ToolViewer)
        viewer_widget.tool = tool

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        list_view_widget = self.query_one("#tool-list", ListView)
        # check if a item is already selected in the list view

        if len(list_view_widget) == 0:
            return

        elif list_view_widget.highlighted_child is None:
            list_view_widget.index = 0
            list_view_widget.action_select_cursor()

        elif list_view_widget.highlighted_child is not None:
            list_view_widget.action_select_cursor()


class HistoryTab(Grid):

    len_history = reactive(0, recompose=True)
    num_tools = reactive(0, recompose=True)

    async def update_history(self) -> None:
        dbm = self.app.config.db_manager
        history = await dbm.get_chat_history(root_id=0)
        self.len_history = len(history.messages)

    async def update_tools(self) -> None:
        dbm = self.app.config.db_manager
        tools = await dbm.get_tools()
        self.num_tools = len(tools)

    async def on_mount(self) -> None:
        self.set_interval(1, self.update_history)
        self.set_interval(1, self.update_tools)

    def compose(self) -> ComposeResult:
        with Container(id="history-contents"):
            yield Markdown(f"## Number of messages: {self.len_history}\n\n## Number of tools: {self.num_tools}")
        with Container(id="history-footer", classes="settings-screen-footer"):
            yield Button("Clear History", variant="error", id="clear-history-button")

    @on(Button.Pressed, "#clear-history-button")
    async def clear_history(self) -> None:
        dbm = self.app.config.db_manager
        await dbm.clear_chat_history()
        self.screen.close_settings()


class SettingsScreen(ModalScreen):
    """Screen with a dialog to display settings."""

    BINDINGS = [("escape", "app.pop_screen", "Dismiss")]

    def compose(self) -> ComposeResult:

        with TabbedContent("User", "Tools", "History", id="settings-screen"):
            # with TabbedContent("User", "History", id="settings-screen"):
            # Tab for user settings
            yield UserSettingsTab(id="user-settings")

            # # Tab for tools settings
            yield ToolSettingsTab(id="tools-tab-grid")

            # Tab for history settings
            yield HistoryTab(id="history-settings")

    def close_settings(self) -> None:
        self.app.pop_screen()
