import asyncio
from datetime import datetime
import os
import json
import logging
import argparse
import shutil
import sqlite3
import aiosqlite
from collections import namedtuple
import functools
from dataclasses import dataclass
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from typing import Any, List, Dict, Optional, Set, Callable

from textual import on
from textual.reactive import reactive
from textual import work
from textual.worker import Worker, get_current_worker
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.containers import ScrollableContainer, Grid, Container, Horizontal, Vertical
from textual.widgets import (
    Footer,
    Header,
    Markdown,
    Static,
    Input,
    DirectoryTree,
    Label,
    Switch,
    Collapsible,
    LoadingIndicator,
    Button,
    TabbedContent,
    ListView,
    ListItem,
    TextArea,
)


from .tools import Tool, InvalidToolError
from .exceptions import ChatMessageError, ToolUpdateError, SubprocessError

from .database.database import ChatMessage, User
from .database.database_sqllite import SQLLiteDatabaseManager
from .files import CodespacesFileManager

from .agents.agents import ReversedAgents
from .agents.autogen_agents import AutoGenAgentManager

from .app_config import AppConfiguration

from .screens.quit_screen import QuitScreen
from .screens.sidebar import Sidebar
from .screens.chat_display import ChatDisplay, ReactiveMessageWidget

from .messages import AppErrorMessage, SelectedReactiveMessage

from .llm import AutoGenChatCompletionService

from .profiler.profiler import Profiler, MessageProfile, ChatProfile, State


class ChatInput(Input):
    """
    A widget for user input.
    """

    def on_mount(self) -> None:
        self.focus()


# class NotificationScreen(ModalScreen):
#     """Screen with a dialog to display notifications."""

#     BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

#     def __init__(self, *args, message: Optional[str] = None, **kwargs):
#         self.message = message or ""
#         super().__init__(*args, **kwargs)

#     def compose(self) -> ComposeResult:
#         with Grid(id="notification-screen-grid"):
#             yield Static(self.message, id="notification")

#             with Grid(id="notification-screen-footer"):
#                 yield Button("Dismiss", variant="primary", id="dismiss-notification")

#     @on(Button.Pressed, "#dismiss-notification")
#     def dismiss(self, result: Any) -> None:  # type: ignore[override]
#         self.app.pop_screen()


# class Title(Static):
#     pass


# class OptionGroup(Container):
#     pass


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


# class CustomMessage(Static):
#     pass


# class CloseScreen(Message):

#     def __init__(self, screen_id: str) -> None:
#         self.screen_id = screen_id
#         super().__init__()


# class HistoryTab(Grid):

#     len_history = reactive(0, recompose=True)
#     num_tools = reactive(0, recompose=True)

#     def update_history(self) -> None:
#         self.len_history = len(fetch_chat_history())

#     def update_tools(self) -> None:
#         self.num_tools = len(APP_CONFIG.get_tools())

#     def on_mount(self) -> None:
#         self.set_interval(1, self.update_history)
#         self.set_interval(1, self.update_tools)

#     def compose(self) -> ComposeResult:
#         with Container(id="history-contents"):
#             yield Markdown(f"## Number of messages: {self.len_history}\n\n## Number of tools: {self.num_tools}")
#         with Container(id="history-footer", classes="settings-screen-footer"):
#             yield Button("Clear History", variant="error", id="clear-history-button")

#     @on(Button.Pressed, "#clear-history-button")
#     def clear_history(self) -> None:
#         APP_CONFIG.clear_chat_history()

#         self.screen.close_settings()


# class UserSettingsTab(Grid):

#     def compose(self) -> ComposeResult:
#         self.widget_user_name = Input(APP_CONFIG.get_user_name())
#         self.widget_user_bio = TextArea(APP_CONFIG.get_user_bio(), id="user-bio")
#         self.widget_user_preferences = TextArea(APP_CONFIG.get_user_preferences(), id="user-preferences")

#         with Grid(id="user-settings-contents"):
#             yield Container(Label("Name", classes="form-label"), self.widget_user_name)
#             with TabbedContent("Bio", "Preferences"):
#                 yield self.widget_user_bio
#                 yield self.widget_user_preferences

#         with Horizontal(classes="settings-screen-footer"):
#             yield Button("Save", variant="primary", id="save-user-settings")

#     @on(Button.Pressed, "#save-user-settings")
#     def save_user_settings(self) -> None:
#         new_user_name = self.widget_user_name.value
#         new_user_bio = self.widget_user_bio.text
#         new_user_preferences = self.widget_user_preferences.text

#         APP_CONFIG.update_configuration(
#             user_name=new_user_name, user_bio=new_user_bio, user_preferences=new_user_preferences
#         )

#         self.screen.close_settings()


# class ToolSettingsTab(Grid):

#     def compose(self) -> ComposeResult:
#         tools = APP_CONFIG.get_tools()
#         # list of tools
#         with Container(id="tool-list-container"):
#             yield ListView(
#                 *(ListItem(Label(tools[tool_id].name), id=f"tool-{tool_id}") for tool_id in tools),
#                 id="tool-list",
#             )
#             yield Button("+", variant="primary", id="new-tool-button")

#         # display the settings for the selected tool
#         with Grid(id="tool-view-grid"):

#             with Vertical():
#                 yield Label("Tool ID", classes="form-label")
#                 yield Input(id="tool-id-input", disabled=True)

#             with Vertical():
#                 yield Label("Tool Name (Display)", classes="form-label")
#                 yield Input(id="tool-name-input")

#             # code editor for the selected tool
#             with Horizontal(id="tool-code-container"):
#                 # yield Label("Code", classes="form-label")
#                 yield TextArea.code_editor("", language="python", id="tool-code-textarea")

#             # footer for the tool view
#             with Horizontal(id="tool-view-footer-grid"):
#                 yield Button("Save", variant="primary", id="save-tool-settings")
#                 yield Button("Delete", variant="error", id="delete-tool-button")

#     @on(Button.Pressed, "#new-tool-button")
#     def create_new_tool(self) -> None:
#         tools = APP_CONFIG.get_tools()

#         new_id = max(tools.keys()) + 1 if tools else 1

#         new_tool_name = f"tool-{new_id}"

#         tool = Tool(new_tool_name, id=new_id)

#         try:
#             tool.validate_tool()
#         except InvalidToolError as e:
#             error_message = f"{e}"
#             self.post_message(AppErrorMessage(error_message))
#             return

#         try:
#             APP_CONFIG.update_tool(tool)
#         except ToolUpdateError as e:
#             error_message = f"{e}"
#             self.post_message(AppErrorMessage(error_message))
#             return

#         list_view_widget = self.query_one("#tool-list", ListView)
#         new_list_item = ListItem(Label(new_tool_name), id=f"tool-{new_id}")

#         list_view_widget.append(new_list_item)
#         num_items = len(list_view_widget)
#         list_view_widget.index = num_items - 1
#         list_view_widget.action_select_cursor()

#     @on(Button.Pressed, "#delete-tool-button")
#     def delete_tool(self) -> None:
#         # get the id of the selected tool
#         tool_id_str = self.query_one("#tool-id-input", Input).value
#         # check if its a valid int
#         try:
#             tool_id = int(tool_id_str)
#         except ValueError:
#             error_message = "Tool ID must be an integer"
#             self.post_message(AppErrorMessage(error_message))
#             return

#         # tool_id = int(self.query_one("#tool-id-input", Input).value)
#         item = self.query_one(f"#tool-{tool_id}", ListItem)
#         # delete the tool from the database
#         try:
#             APP_CONFIG.delete_tool(tool_id)
#         except ToolUpdateError as e:
#             error_message = f"{e}"
#             self.post_message(AppErrorMessage(error_message))
#             return

#         # remove the tool from the list view
#         item.remove()

#         list_view_widget = self.query_one("#tool-list", ListView)

#         if len(list_view_widget) > 0:
#             list_view_widget.action_cursor_up()
#             list_view_widget.action_select_cursor()
#         else:
#             self.query_one("#tool-code-textarea", TextArea).text = ""
#             self.query_one("#tool-name-input", Input).value = ""
#             self.query_one("#tool-id-input", Input).value = ""

#     @on(Button.Pressed, "#save-tool-settings")
#     def save_tool_settings(self) -> None:
#         # get the id of the selected tool
#         tool_id = int(self.query_one("#tool-id-input", Input).value)
#         tool_name = self.query_one("#tool-name-input", Input).value
#         tool_code = self.query_one("#tool-code-textarea", TextArea).text

#         tool = Tool(tool_name, tool_code, id=tool_id)

#         try:
#             tool.validate_tool()
#         except InvalidToolError as e:
#             error_message = f"{e}"
#             self.post_message(AppErrorMessage(error_message))
#             return

#         try:
#             APP_CONFIG.update_tool(tool)
#         except ToolUpdateError as e:
#             error_message = f"{e}"
#             self.post_message(AppErrorMessage(error_message))
#             return

#         item_label = self.query_one(f"#tool-{tool_id} > Label", Label)
#         item_label.update(tool_name)
#         self.screen.close_settings()

#     def on_list_view_selected(self, event: ListView.Selected) -> None:
#         tool_id = int(event.item.id[5:])
#         tool = APP_CONFIG.get_tools(tool_id)[tool_id]
#         if tool:
#             self.query_one("#tool-code-textarea", TextArea).text = tool.code
#             self.query_one("#tool-name-input", Input).value = tool.name
#             self.query_one("#tool-id-input", Input).value = str(tool_id)
#         else:
#             self.app.post_message(AppErrorMessage("Tool not found"))

#     def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
#         list_view_widget = self.query_one("#tool-list", ListView)
#         # check if a item is already selected in the list view

#         if len(list_view_widget) == 0:
#             return

#         elif list_view_widget.highlighted_child is None:
#             list_view_widget.index = 0
#             list_view_widget.action_select_cursor()

#         elif list_view_widget.highlighted_child is not None:
#             list_view_widget.action_select_cursor()


# class SettingsScreen(ModalScreen):
#     """Screen with a dialog to display settings."""

#     BINDINGS = [("escape", "app.pop_screen", "Dismiss")]

#     def compose(self) -> ComposeResult:

#         with TabbedContent("User", "Tools", "History", id="settings-screen"):
#             # Tab for user settings
#             yield UserSettingsTab(id="user-settings")

#             # Tab for tools settings
#             yield ToolSettingsTab(id="tools-tab-grid")

#             # Tab for history settings
#             yield HistoryTab(id="history-settings")

#     def close_settings(self) -> None:
#         self.app.pop_screen()


class ProfileNode(Static):

    message_profile: MessageProfile

    DEFAULT_CSS = """
    ProfileNode Markdown {
        border: solid $primary;
        padding: 1;
    }
"""

    def compose(self) -> ComposeResult:
        states = self.message_profile.states

        def state_name_comparator(x: State, y: State):
            return x.name < y.name

        states.sort(key=functools.cmp_to_key(state_name_comparator))

        state_display_str = " ".join([str(state) for state in states])

        with Collapsible(collapsed=True, title=state_display_str):
            yield Static(str(self.message_profile))
            yield Markdown(str(self.message_profile.message))


class ProfileDiagram(ScrollableContainer):

    chat_profile: ChatProfile = reactive(None, recompose=True)

    def compose(self) -> ComposeResult:

        if self.chat_profile is None:
            yield Label("Profiling...")
            yield LoadingIndicator()
            return

        num_messages = self.chat_profile.num_messages
        yield Label(f"Number of messages: {num_messages}", classes="heading")
        for message_profile in self.chat_profile.message_profiles:
            node = ProfileNode()
            node.message_profile = message_profile
            yield node


class ProfilerContainer(Container):

    chat_history = reactive(None)
    profile_diagram = None

    def __init__(self, *args, root_id: int = -1, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_id = root_id

    def on_mount(self) -> None:
        self.set_interval(1, self.update_chat_history)

    async def update_chat_history(self) -> None:
        dbm = self.app.config.db_manager
        self.chat_history = await dbm.get_chat_history(self.root_id)

    def watch_chat_history(self, new_chat_history) -> None:
        if new_chat_history is None:
            return

        self.start_profiling()

    @work(thread=True, exclusive=True)
    async def start_profiling(self):
        chat_profile = await self.profile_chat()
        if self.profile_diagram is None:
            self.profile_diagram = ProfileDiagram()
        self.profile_diagram.chat_profile = chat_profile

    async def profile_chat(self) -> ChatProfile:
        llm_service = self.app.config.llm_service
        profiler = Profiler(llm_service=llm_service)

        message_profile_list = []

        for message in self.chat_history.messages:
            msg_profile = profiler.profile_message(message)
            message_profile_list.append(msg_profile)

        chat_profile = ChatProfile(num_messages=len(self.chat_history.messages), message_profiles=message_profile_list)

        return chat_profile

    def compose(self):
        if self.profile_diagram is None:
            self.profile_diagram = ProfileDiagram()
        yield self.profile_diagram


class MonitoringScreen(ModalScreen):
    """A screen that displays a chat history"""

    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    def __init__(self, *args, root_id: int = -1, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_id = root_id

    def compose(self) -> ComposeResult:

        # dbm = self.app.config.db_manager
        # history = dbm.get_chat_history(self.root_msg_id)

        with Grid(id="chat-screen"):

            with Container(id="chat-screen-header"):
                yield Label(f"Monitoring 🧵 Thread: {self.root_id}", classes="heading")

            with TabbedContent("Overview", "Details", id="chat-screen-tabs"):
                # with TabbedContent("Details", id="chat-screen-tabs"):

                profiler = ProfilerContainer(id="chat-profiler", root_id=self.root_id)
                yield profiler

                with ScrollableContainer(id="chat-screen-contents"):
                    yield ChatDisplay(root_id=self.root_id)

            # with Horizontal(id="chat-screen-footer"):
            # yield Button("Learn New Tool", variant="error", id="learn")

    # @on(Button.Pressed, "#learn")
    # def learn(self) -> None:
    #     learning_screen = LearningScreen()
    #     learning_screen.root_msg_id = self.root_msg_id
    #     self.app.push_screen(learning_screen)


# class LearningScreen(ModalScreen):

#     BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

#     root_msg_id = None

#     def compose(self) -> ComposeResult:
#         with Grid(id="learning-screen"):
#             yield Horizontal(Label("Interactive Tool Learning", classes="heading"), id="learning-screen-header")
#             yield ScrollableContainer(
#                 TextArea.code_editor(
#                     f"""
#                     # Learning a function for {self.root_msg_id}
#                     """,
#                     language="python",
#                 ),
#                 id="learning-screen-contents",
#             )
#             with Horizontal(id="learning-screen-footer"):
#                 # yield Button("Start", variant="error", id="start-learning")
#                 yield Button("Save", variant="primary", id="save")

#     def on_mount(self) -> None:
#         self.start_learning()

#     @on(Button.Pressed, "#save")
#     def save(self) -> None:
#         widget = self.query_one("#learning-screen-contents > TextArea", TextArea)
#         code = widget.text
#         name = code.split("\n")[0][1:]

#         tool = Tool(name, code)
#         try:
#             tool.validate_tool()
#             APP_CONFIG.update_tool(tool)
#             self.app.pop_screen()
#             self.app.push_screen(NotificationScreen(message="Tool saved successfully"))

#         except InvalidToolError as e:
#             error_message = f"{e}"
#             self.post_message(AppErrorMessage(error_message))
#             return

#         except ToolUpdateError as e:
#             error_message = f"{e}"
#             self.post_message(AppErrorMessage(error_message))
#             return

#     @work(thread=True)
#     async def start_learning(self) -> None:
#         widget = self.query_one("#learning-screen-contents > TextArea", TextArea)
#         widget.text = "# Learning..."

#         history = await a_fetch_chat_history(self.root_msg_id)
#         name, code = learn_tool_from_history(history)

#         widget.text = "#" + name + "\n" + code


# def learn_tool_from_history(history: List[Dict[str, str]]) -> str:

#     # return "hola"

#     markdown = ""
#     for msg in history:
#         markdown += f"{msg['role']}: {msg['content']}\n"

#     agent = ConversableAgent(
#         "learning_assistant",
#         llm_config=LLM_CONFIG,
#         system_message="""You are a helpful assistant that for the given chat
# history can return a standalone, documented python function.

# Try to extract a most general version of the function based on the chat history.
# That can be reused in the future for similar tasks. Eg do not use hardcoded arguments.
# Instead make them function parameters.

# The chat history contains a task the agents were trying to accomplish.
# Analyze the following chat history to assess if the task was completed,
# and if it was return the python function that would accomplish the task.
#         """,
#     )
#     messages = [
#         {
#             "role": "user",
#             "content": f"""The chat history is

#             {markdown}

#             Only generate a single python function in code blocks and nothing else.
#             Make sure all imports are inside the function.
#             Both ast.FunctionDef, ast.AsyncFunctionDef are acceptable.

#             Function signature should be annotated properly.
#             Function should return a string as the final result.
#             """,
#         }
#     ]
#     reply = agent.generate_reply(messages)
#     from autogen.code_utils import extract_code

#     # extract a code block from the reply
#     code_blocks = extract_code(reply)
#     lang, code = code_blocks[0]

#     messages.append({"role": "assistant", "content": code})

#     messages.append(
#         {
#             "role": "user",
#             "content": """suggest a max two word english phrase that is a friendly
#           display name for the function. Only reply with the name in a code block.
#           no need to use an quotes or code blocks. Just two words.""",
#         }
#     )

#     name = agent.generate_reply(messages)

#     return name, code


# def generate_response_process(msg_idx: int):
#     chat_history = fetch_chat_history()
#     task = chat_history[msg_idx]["content"]

#     def terminate_on_consecutive_empty(recipient, messages, sender, **kwargs):
#         # check the contents of the last N messages
#         # if all empty, terminate
#         consecutive_are_empty = None
#         last_n = 2

#         for message in reversed(messages):
#             if last_n == 0:
#                 break
#             if message["role"] == "user":
#                 last_n -= 1
#                 if len(message["content"]) == 0:
#                     consecutive_are_empty = True
#                 else:
#                     consecutive_are_empty = False
#                     break

#         if consecutive_are_empty:
#             return True, "TERMINATE"

#         return False, None

#     def summarize(text):
#         return text[:100]

#     def post_snippet_and_record_history(sender, message, recipient, silent):
#         if silent is True:
#             return message

#         if isinstance(message, str):
#             summary = message
#             insert_chat_message(sender.name, message, root_id=msg_idx + 1)
#         elif isinstance(message, Dict):
#             if message.get("content"):
#                 summary = message["content"]
#                 insert_chat_message(sender.name, message["content"], root_id=msg_idx + 1)
#             elif message.get("tool_calls"):
#                 tool_calls = message["tool_calls"]
#                 summary = "Calling tools…"
#                 insert_chat_message(sender.name, json.dumps(tool_calls), root_id=msg_idx + 1)
#             else:
#                 raise ValueError("Message must have a content or tool_calls key")

#         snippet = summarize(summary)
#         insert_chat_message("info", snippet, root_id=0, id=msg_idx + 1)
#         return message

#     tools = APP_CONFIG.get_tools()

#     functions = []
#     for tool in tools.values():
#         func = FunctionWithRequirements.from_str(tool.code)
#         functions.append(func)
#     executor = LocalCommandLineCodeExecutor(work_dir=APP_CONFIG.get_workdir(), functions=functions)

#     system_message = APP_CONFIG.get_assistant_system_message()
#     system_message += executor.format_functions_for_prompt()

#     assistant = AssistantAgent(
#         "assistant",
#         llm_config=LLM_CONFIG,
#         system_message=system_message,
#     )
#     user = UserProxyAgent(
#         "user",
#         code_execution_config={"executor": executor},
#         human_input_mode="NEVER",
#         is_termination_msg=lambda x: x.get("content") and "TERMINATE" in x.get("content", ""),
#     )

#     # populate the history before registering new reply functions
#     for msg in chat_history:
#         if msg["role"] == "user":
#             user.send(msg["content"], assistant, request_reply=False, silent=True)
#         else:
#             assistant.send(msg["content"], user, request_reply=False, silent=True)

#     assistant.register_reply([Agent, None], terminate_on_consecutive_empty)
#     assistant.register_hook("process_message_before_send", post_snippet_and_record_history)
#     user.register_hook("process_message_before_send", post_snippet_and_record_history)

#     logging.info("Current history:")
#     logging.info(assistant.chat_messages[user])

#     # hack to get around autogen's current api...
#     initial_reply = assistant.generate_reply(None, user)
#     assistant.initiate_chat(user, message=initial_reply, clear_history=False, silent=False)

#     # user.send(task, assistant, request_reply=True, silent=False)

#     user.send(
#         f"""Based on the results in above conversation, create a response for the user.
# While computing the response, remember that this conversation was your inner mono-logue. The user does not need to know every detail of the conversation.
# All they want to see is the appropriate result for their task (repeated below) in a manner that would be most useful.
# The task was: {task}

# There is no need to use the word TERMINATE in this response.
#         """,
#         assistant,
#         request_reply=False,
#         silent=True,
#     )
#     response = assistant.generate_reply(assistant.chat_messages[user], user)
#     assistant.send(response, user, request_reply=False, silent=True)

#     response = assistant.chat_messages[user][-1]["content"]

#     insert_chat_message("assistant", response, root_id=0, id=msg_idx + 1)


class TinyRA(App):
    """
    Main application for TinyRA.
    """

    BINDINGS = [
        ("ctrl+b", "toggle_sidebar", "Work Directory"),
        ("ctrl+c", "request_quit", "Quit"),
        # ("ctrl+s", "request_settings", "Settings"),
    ]

    CSS_PATH = ["tui.css", Path("screens") / "sidebar.css"]

    TITLE = "TinyRA"
    SUB_TITLE = "A minimalistic, long-lived research assistant"

    def __init__(self, *args, app_config: AppConfiguration, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = app_config
        self.logger = logging.getLogger(__name__)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        yield Header(show_clock=True)

        yield Sidebar(classes="-hidden", id="sidebar")

        with Grid(id="chat-grid"):
            yield ChatDisplay(id="chat-history", root_id=0)
            yield ChatInput(id="chat-input-box")

        yield Footer()

    def action_request_quit(self) -> None:

        def check_quit(quit: bool) -> None:
            if quit:
                self.workers.cancel_all()
                self.exit(message="Exiting TinyRA...")

        self.push_screen(QuitScreen(), check_quit)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    # def action_request_settings(self) -> None:
    #     self.push_screen(SettingsScreen())

    # def action_toggle_sidebar(self) -> None:
    #     self.logger.info("Toggling sidebar.")
    #     sidebar = self.query_one(Sidebar)
    #     if sidebar.has_class("-hidden"):
    #         sidebar.remove_class("-hidden")
    #     else:
    #         sidebar.add_class("-hidden")

    def action_toggle_sidebar(self) -> None:
        self.logger.info("Toggling sidebar.")
        sidebar = self.query_one(Sidebar)
        self.set_focus(None)
        if sidebar.has_class("-hidden"):
            sidebar.remove_class("-hidden")
        else:
            if sidebar.query("*:focus"):
                self.screen.set_focus(None)
            sidebar.add_class("-hidden")

    # @on(AppErrorMessage)
    # def notify_error_to_user(self, event: AppErrorMessage) -> None:
    #     self.push_screen(NotificationScreen(message=event.message))

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

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = self.query_one("#chat-input-box", Input).value.strip()
        self.query_one(Input).value = ""
        self.handle_input(user_input)

    @on(SelectedReactiveMessage)
    def on_reactive_message_selected(self, message: SelectedReactiveMessage) -> None:
        """Called when a reactive assistant message is selected."""
        message = message.message
        self.logger.info(f"Click on a reactive message {message}")
        new_chat_screen = MonitoringScreen(root_id=message.id)
        self.push_screen(new_chat_screen)

    @work()
    async def handle_input(self, user_input: str) -> None:
        chat_display_widget = self.query_one(ChatDisplay)

        dbm = self.app.config.db_manager
        user = await dbm.get_user()

        # display the user input in the chat display
        self.logger.info(f"User input: {user_input}")

        new_chat_message = ChatMessage(role="user", content=user_input, root_id=0, timestamp=datetime.now().timestamp())
        self.logger.info(str(new_chat_message))
        new_chat_message = await dbm.set_chat_message(new_chat_message)
        reactive_message = ReactiveMessageWidget(new_chat_message, user)
        await chat_display_widget.mount(reactive_message)

        assistant_message = ChatMessage(
            role="info", content="Computing response…", root_id=0, timestamp=datetime.now().timestamp()
        )
        self.logger.info("Mounting a new assistant chat widget")
        assistant_message = await self.config.db_manager.set_chat_message(assistant_message)
        reactive_message = ReactiveMessageWidget(assistant_message, user)
        await chat_display_widget.mount(reactive_message)
        reactive_message.scroll_visible()  # Fix: This is a hack to make the container scroll; Not sure why on_mount doesn't handle

        def update_callback(update: str) -> None:
            assistant_message.role = "info"
            assistant_message.content = update
            self.config.db_manager.sync_set_chat_message(assistant_message)

        try:
            self.logger.info(f"Generating response for {new_chat_message}")
            self.generate_response(new_chat_message, assistant_message, update_callback)
        except SubprocessError as e:
            error_message = f"{e}"
            await dbm.set_chat_message("error", error_message, root_id=0, id=id + 1)
            self.post_message(AppErrorMessage(error_message))

    @work(thread=True)
    async def generate_response(self, *args) -> None:
        """
        Run the agents in a separate thread because AutoGen may block the main thread.
        But allow the worker to be canceled if the user cancels the operation.
        Worker can be cancelled between non-blocking operations in the thread.
        """
        worker = get_current_worker()  # this is the worker running this thread
        task = asyncio.create_task(self.config.agent_manager.generate_response(*args))

        while not task.done():
            self.logger.debug(f"Waiting for task to complete, {worker}")
            if worker.is_cancelled:
                self.logger.info(f"Canceling the worker, {worker}")
                task.cancel()
                return
            await asyncio.sleep(1)  # sleep for a short time before checking again

        out_message = await task
        out_message = await self.config.db_manager.set_chat_message(out_message)
        self.logger.info(str(out_message))

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Called when the worker state changes."""
        self.logger.info(event)


def run_app() -> None:
    """
    Run the TinyRA app.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-app", action="store_true", help="Reset entire app.")
    parser.add_argument("--reset-db", action="store_true", help="Reset database")
    parser.add_argument("--reset-files", action="store_true", help="Reset files")
    args = parser.parse_args()

    app_path = Path.home() / ".tinyra"
    work_dir = app_path / "work_dir"
    logging.basicConfig(
        filename=app_path / "app.log", level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger(__name__)

    db_manager = SQLLiteDatabaseManager(data_path=app_path)
    file_manager = CodespacesFileManager(root_path=work_dir)
    llm_service = AutoGenChatCompletionService(llm_config=None)

    # agent_manager = ReversedAgents()
    agent_manager = AutoGenAgentManager(llm_config=None, db_manager=db_manager, file_manager=file_manager)

    app_config = AppConfiguration(
        app_path=None,
        db_manager=db_manager,
        file_manager=file_manager,
        agent_manager=agent_manager,
        llm_service=llm_service,
    )

    if args.reset_app:
        print("Warning: Would you like to reset the whole app?")
        print("Press enter to continue or Ctrl+C to cancel.")
        input()
        app_config.reset()
        exit()

    if args.reset_db:
        print("Warning: Reset the database?")
        print("Press enter to continue or Ctrl+C to cancel.")
        input()
        success = asyncio.run(app_config.db_manager.reset())
        if success:
            print("Database reset successful.")
        else:
            print("Database reset failed.")
        exit()

    if args.reset_files:
        print("Warning: Reset the files?")
        print("Press enter to continue or Ctrl+C to cancel.")
        input()
        app_config.file_manager.reset()
        exit()

    logger.info("Initializing the app")
    try:
        asyncio.run(app_config.initialize())
    except Exception as e:
        logger.error(e)
        raise e

    app = TinyRA(app_config=app_config)
    app.run()


if __name__ == "__main__":
    run_app()
