import asyncio
from datetime import datetime
import logging
import argparse
from pathlib import Path

from textual import on
from textual import work
from textual.worker import Worker, get_current_worker
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import (
    Footer,
    Header,
    Input,
)


from .exceptions import SubprocessError
from .messages import SelectedReactiveMessage, UserNotificationError, UserNotificationSuccess

from .llm import AutoGenChatCompletionService
from .database.database import ChatMessage
from .database.database_sqllite import SQLLiteDatabaseManager
from .files import CodespacesFileManager
from .agents.autogen_agents import AutoGenAgentManager, AGMPlusTools
from .app_config import AppConfiguration

from .screens.quit_screen import QuitScreen
from .screens.sidebar import Sidebar
from .screens.chat_display import ChatDisplay, message_display_handler
from .screens.settings import SettingsScreen
from .screens.notifications import NotificationScreenError, NotificationScreenSuccess
from .screens.monitoring import MonitoringScreen


class ChatInput(Input):
    """
    A widget for user input.
    """

    def on_mount(self) -> None:
        self.focus()


class TinyRA(App):
    """
    Main application for TinyRA.
    """

    BINDINGS = [
        ("ctrl+b", "toggle_sidebar", "Work Directory"),
        ("ctrl+c", "request_quit", "Quit"),
        ("ctrl+s", "request_settings", "Settings"),
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

    def action_request_settings(self) -> None:
        self.push_screen(SettingsScreen())

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

    @on(UserNotificationError)
    def notify_error_to_user(self, event: UserNotificationError) -> None:
        self.push_screen(NotificationScreenError(message=event.message))

    @on(UserNotificationSuccess)
    def notify_success_to_user(self, event: UserNotificationSuccess) -> None:
        self.push_screen(NotificationScreenSuccess(message=event.message))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = self.query_one("#chat-input-box", Input).value.strip()
        self.query_one(Input).value = ""
        self.handle_input(user_input)

    @on(SelectedReactiveMessage)
    def on_reactive_message_selected(self, message: SelectedReactiveMessage) -> None:
        """Called when a reactive assistant message is selected."""
        message = message.message
        self.logger.info(f"Click on a reactive message {message}")

        # only allow profiling of root messages
        if message.root_id != 0:
            return

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
        reactive_message = message_display_handler(new_chat_message, user)
        await chat_display_widget.mount(reactive_message)

        assistant_message = ChatMessage(
            role="info", content="Computing response…", root_id=0, timestamp=datetime.now().timestamp()
        )
        self.logger.info("Mounting a new assistant chat widget")
        assistant_message = await self.config.db_manager.set_chat_message(assistant_message)
        reactive_message = message_display_handler(assistant_message, user)
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
            self.post_message(UserNotificationError(error_message))

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
    # if app_path does not exist, create it
    app_path.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=app_path / "app.log", level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger(__name__)

    db_manager = SQLLiteDatabaseManager(data_path=app_path)
    file_manager = CodespacesFileManager(root_path=work_dir)
    llm_service = AutoGenChatCompletionService(llm_config=None)

    # agent_manager = ReversedAgents()
    # agent_manager = AutoGenAgentManager(llm_config=None, db_manager=db_manager, file_manager=file_manager)
    agent_manager = AGMPlusTools(llm_config=None, db_manager=db_manager, file_manager=file_manager)

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
