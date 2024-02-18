import os
import asyncio
import ast
import configparser
import platform
import json
import logging
import argparse
import shutil
import sqlite3
import aiosqlite

from typing import List, Dict

from textual import work
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import ScrollableContainer, Grid, Container
from textual.widget import Widget
from textual.widgets import Footer, Header, Markdown, Static, Input, DirectoryTree, Label
from textual.widgets import Button
from textual.widgets import TextArea
from textual.reactive import reactive
from textual.message import Message
from textual.events import Key

from autogen import config_list_from_json
from autogen import Agent, AssistantAgent, UserProxyAgent


class AppConfiguration:
    def __init__(
        self,
        data_path: str = os.path.join(os.path.expanduser("~"), ".tinyra"),
        database: str = "app.db",
    ):
        # set the default path to a dir in user's home directory if not specified
        self._data_path = data_path
        # database must reside in the data path
        self._database_path = os.path.join(data_path, database)

        # create the data path if it does not exist
        if not os.path.exists(self._data_path):
            os.makedirs(self._data_path)

        # initialize the database
        self._init_database()

    def get_database_path(self):
        return self._database_path

    def get_user_name(self):
        """Query the database for user's name"""
        conn = sqlite3.connect(self._database_path)
        c = conn.cursor()
        c.execute("SELECT user_name FROM configuration")
        user_name = c.fetchone()[0]
        conn.close()
        return user_name

    def get_user_bio(self):
        """Query the database for user's bio"""
        conn = sqlite3.connect(self._database_path)
        c = conn.cursor()
        c.execute("SELECT user_bio FROM configuration")
        user_bio = c.fetchone()[0]
        conn.close()
        return user_bio

    def update_configuration(self, user_name: str = None, user_bio: str = None):
        """Update the user's name and bio in the database"""
        conn = sqlite3.connect(self._database_path)
        c = conn.cursor()
        if user_name:
            c.execute("UPDATE configuration SET user_name = ?", (user_name,))
        if user_bio:
            c.execute("UPDATE configuration SET user_bio = ?", (user_bio,))
        conn.commit()
        conn.close()

    def _init_database(self):
        """
        Initialize the chat history and configuration database.
        """
        conn = sqlite3.connect(self._database_path)

        # Create a cursor object
        cursor = conn.cursor()

        # Create chat_history table if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                root_id INTEGER NOT NULL,
                id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                PRIMARY KEY (root_id, id)
            )
            """
        )

        # Check if the configuration table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configuration'")
        if cursor.fetchone() is None:
            # The configuration table does not exist, so create it
            cursor.execute(
                """
                CREATE TABLE configuration (
                    user_name TEXT NOT NULL,
                    user_bio TEXT
                )
            """
            )

            user_name = os.environ.get("USER", "default_user")
            user_bio = "default_bio"

            # Insert data into the configuration table
            cursor.execute(
                """
                INSERT INTO configuration VALUES (?, ?)
            """,
                (user_name, user_bio),
            )

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

    def get_meta_system_message(self):
        user_name = self.get_user_name()
        user_bio = self.get_user_bio()
        operating_system = platform.uname().system

        return f"""
        You are a helpful researcher assistant named "TinyRA".
        When introducing yourself do not forget your name!

        You are running on operating system with the following config:
        {operating_system}

        You are here to help "{user_name}" with his research.

        The following is the bio of {user_name}:
        <bio>
        {user_bio}
        </bio>

        Respond to {user_bio}'s messages to be most helpful.

        """

    def get_assistant_system_message(self):
        return (
            self.get_meta_system_message()
            + "\nAdditional instructions\n"
            + AssistantAgent.DEFAULT_SYSTEM_MESSAGE
            + "\n\nReply with TERMINATE when the task is done. Especially if the user is chit-chatting with you."
        )

    def get_data_path(self):
        return self._data_path


APP_CONFIG = AppConfiguration()
# do not save the LLM config to the database, keep it
LLM_CONFIG = config_list_from_json("OAI_CONFIG_LIST")[0]


logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(APP_CONFIG.get_data_path(), "app.log"),
    filemode="w",
    format="%(asctime)-15s %(message)s",
)


def fetch_chat_history(root_id: int = 0) -> List[Dict[str, str]]:
    """
    Fetch the chat history from the database.

    Args:
        root_id: the root id of the messages to fetch. If None, all messages are fetched.

    Returns:
        A list of chat messages.
    """
    conn = sqlite3.connect(APP_CONFIG.get_database_path())
    c = conn.cursor()
    c.execute("SELECT root_id, id, role, content FROM chat_history WHERE root_id = ?", (root_id,))
    chat_history = [
        {"root_id": root_id, "id": id, "role": role, "content": content} for root_id, id, role, content in c.fetchall()
    ]
    conn.close()
    return chat_history


def fetch_row(id: int, root_id: int = 0) -> Dict[str, str]:
    """
    Fetch a single row from the database.

    Args:
        id: the id of the row to fetch
        root_id: the root id of the row to fetch. If not specified, it's assumed to be 0.

    Returns:
        A single row from the database.
    """
    conn = sqlite3.connect(APP_CONFIG.get_database_path())
    c = conn.cursor()
    c.execute("SELECT role, content FROM chat_history WHERE id = ? AND root_id = ?", (id, root_id))
    row = [{"role": role, "content": content, "id": id, "root_id": root_id} for role, content in c.fetchall()]
    conn.close()
    return row[0] if row else None


def insert_chat_message(role: str, content: str, root_id: int, id: int = None) -> int:
    """
    Insert a chat message into the database.

    Args:
        role: the role of the message
        content: the content of the message
        root_id: the root id of the message
        id: the id of the row to update. If None, a new row is inserted.

    Returns:
        The id of the inserted (or modified) row.
    """
    try:
        with sqlite3.connect(APP_CONFIG.get_database_path()) as conn:
            c = conn.cursor()
            if id is None:
                c.execute("SELECT MAX(id) FROM chat_history WHERE root_id = ?", (root_id,))
                max_id = c.fetchone()[0]
                id = max_id + 1 if max_id is not None else 0
                data = (root_id, id, role, content)
                c.execute("INSERT INTO chat_history (root_id, id, role, content) VALUES (?, ?, ?, ?)", data)
                conn.commit()
                return id
            else:
                c.execute("SELECT * FROM chat_history WHERE root_id = ? AND id = ?", (root_id, id))
                if c.fetchone() is None:
                    data = (root_id, id, role, content)
                    c.execute("INSERT INTO chat_history (root_id, id, role, content) VALUES (?, ?, ?, ?)", data)
                    conn.commit()
                    return id
                else:
                    data = (role, content, root_id, id)
                    c.execute("UPDATE chat_history SET role = ?, content = ? WHERE root_id = ? AND id = ?", data)
                    conn.commit()
                    return id
    except sqlite3.Error as e:
        print(f"Error inserting or updating chat message: {e}")


async def a_insert_chat_message(role: str, content: str, root_id: int, id: int = None) -> int:
    """
    Insert a chat message into the database.

    Args:
        role: the role of the message
        content: the content of the message
        root_id: the root id of the message
        id: the id of the row to update. If None, a new row is inserted.

    Returns:
        The id of the inserted (or modified) row.
    """
    try:
        async with aiosqlite.connect(APP_CONFIG.get_database_path()) as conn:
            c = await conn.cursor()
            if id is None:
                await c.execute("SELECT MAX(id) FROM chat_history WHERE root_id = ?", (root_id,))
                max_id = (await c.fetchone())[0]
                id = max_id + 1 if max_id is not None else 0
                data = (root_id, id, role, content)
                await c.execute("INSERT INTO chat_history (root_id, id, role, content) VALUES (?, ?, ?, ?)", data)
                await conn.commit()
                return id
            else:
                await c.execute("SELECT * FROM chat_history WHERE root_id = ? AND id = ?", (root_id, id))
                if await c.fetchone() is None:
                    data = (root_id, id, role, content)
                    await c.execute("INSERT INTO chat_history (root_id, id, role, content) VALUES (?, ?, ?, ?)", data)
                    await conn.commit()
                    return id
                else:
                    data = (role, content, root_id, id)
                    await c.execute("UPDATE chat_history SET role = ?, content = ? WHERE root_id = ? AND id = ?", data)
                    await conn.commit()
                    return id
    except aiosqlite.Error as e:
        print(f"Error inserting or updating chat message: {e}")


def function_names_to_markdown_table(file_path: str) -> str:
    """
    Given a python file, extract the function names and docstrings
    and return them as a markdown table.

    Args:
        file_path: the path to the python file

    Returns:
        A markdown table with function names and docstrings.
    """
    with open(file_path, "r") as f:
        content = f.read()
    tree = ast.parse(content)

    table = "## Available Functions\n\n"
    for i, item in enumerate(tree.body):
        if isinstance(item, ast.FunctionDef):
            name = item.name
            docstring = ast.get_docstring(item) or "No docstring available"
            docstring = docstring.split("\n")[0]
            table += f"- `{name}`: \n{docstring}\n"
    return table


def get_available_functions() -> str:
    """
    Get the available functions from the agent_utils.py file
    and return them as a markdown table.
    """
    UTILS_FILE = os.path.join(APP_CONFIG.get_data_path(), "agent_utils.py")
    if not os.path.exists(UTILS_FILE):
        # create the file if it does not exist
        with open(UTILS_FILE, "w") as f:
            f.write("")

    markdown_table = function_names_to_markdown_table(UTILS_FILE)
    return markdown_table


def json_to_markdown_code_block(json_data: dict, pretty_print: bool = True) -> str:
    """
    Converts a JSON object to a markdown code block.

    Args:
        json_data (dict): The JSON object to convert.
        pretty_print (bool, optional): Whether to pretty print the JSON. Defaults to True.

    Returns:
        str: The markdown code block representing the JSON object.
    """
    if pretty_print:
        json_string = json.dumps(json_data, indent=2)
    else:
        json_string = json.dumps(json_data)

    markdown_code_block = f"```json\n{json_string}\n```"
    return markdown_code_block


def message2markdown(message: Dict[str, str]) -> str:
    """
    Convert a message to markdown that can be displayed in the chat display.

    Args:
        message: a message

    Returns:
        A markdown string.
    """
    role = message["role"]
    if role == "user":
        display_name = APP_CONFIG.get_user_name()
    else:
        display_name = "TinyRA"

    if role == "info":
        display_id = "\U0001F4AD" * 3
    else:
        display_id = message["id"]

    content = message["content"]

    return f"[{display_id}] {display_name}: {content}"


class ReactiveAssistantMessage(Markdown):
    """
    A reactive markdown widget for displaying assistant messages.
    """

    message = reactive({"role": "assistant", "content": "loading...", "id": -1})

    class Selected(Message):
        """Assistant message selected message."""

        def __init__(self, msg_id: str) -> None:
            self.msg_id = msg_id
            super().__init__()

    def set_id(self, msg_id):
        self.msg_id = msg_id
        # self.message = fetch_row(self.msg_id)

    def on_mount(self) -> None:
        self.set_interval(1, self.update_message)

    def on_click(self) -> None:
        self.post_message(self.Selected(self.msg_id))

    def update_message(self):
        self.message = fetch_row(self.msg_id)
        self.classes = f"{self.message['role'].lower()}-message message"

    def watch_message(self) -> str:
        self.update(message2markdown(self.message))


def message_display_handler(message: Dict[str, str]) -> Markdown or ReactiveAssistantMessage:
    """
    Given a message, return a widget for displaying the message.
    If the message is from the user, return a markdown widget.
    If the message is from the assistant, return a reactive markdown widget.

    Args:
        message: a message

    Returns:
        A markdown widget or a reactive markdown widget.
    """
    role = message["role"]
    if role == "user":
        text = Markdown(message2markdown(message), classes=f"{role.lower()}-message message")
    else:
        id = message["id"]
        text = ReactiveAssistantMessage(classes=f"{role.lower()}-message message")
        text.set_id(id)
    return text


class SkillsDisplayContainer(ScrollableContainer):
    """
    A container for displaying the available skills.
    """

    def compose(self) -> ComposeResult:
        yield SkillsDisplay()


class DirectoryTreeContainer(ScrollableContainer):
    """
    A container for displaying the directory tree.
    """

    dirpath = os.path.join(APP_CONFIG.get_data_path(), "work_dir")
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    dir_contents = reactive(str(os.listdir(dirpath)))

    def compose(self) -> ComposeResult:
        yield DirectoryTree(self.dirpath)

    def on_mount(self) -> None:
        self.set_interval(1, self.update_dir_contents)

    def update_dir_contents(self) -> None:
        self.dir_contents = str(os.listdir(self.dirpath))

    def watch_dir_contents(self):
        self.query_one(DirectoryTree).reload()


class SkillsDisplay(Markdown):
    """
    A markdown widget for displaying the available skills.
    """

    skills = reactive(get_available_functions)

    def watch_skills(self) -> None:
        self.update(self.skills)

    def on_mount(self) -> None:
        self.set_interval(5, self.update_skills)

    def update_skills(self):
        self.skills = get_available_functions()


class ChatDisplay(ScrollableContainer):
    """
    A container for displaying the chat history.

    The chat history is fetched from the database and displayed.
    Its updated every second.

    When a new message is detected, it is mounted to the container.
    """

    limit_history = 100
    chat_history = reactive(fetch_chat_history)
    old_chat_history = reactive(fetch_chat_history)

    async def on_mount(self) -> None:
        self.set_interval(1.0, self.update_chat_history)
        logging.info("Waiting 2 sec for message mounting to complete.")
        await asyncio.sleep(2)
        logging.info("Scrolling to end of container.")
        self.scroll_end()

    def update_chat_history(self) -> None:
        self.chat_history = fetch_chat_history()

    async def watch_chat_history(self) -> None:
        len_old = len(self.old_chat_history)
        len_new = len(self.chat_history)
        if len_new > len_old:
            logging.info("New message detected. Mounting them.")
            # add widgets for new messages
            for i in range(len_old, len_new):
                logging.info(f"Mounting message {i}")
                text = message_display_handler(self.chat_history[i])
                self.mount(text)

                # text.scroll_visible(animate=False)
                self.scroll_end()
                logging.info(f"Scrolling to message {i}")
        self.old_chat_history = self.chat_history

    def compose(self) -> ComposeResult:
        for message in self.chat_history[-self.limit_history :]:
            widget = message_display_handler(message)
            yield widget


class ChatInput(Static):
    """
    A widget for user input.
    """

    def on_mount(self) -> None:
        input = self.query_one(Input)
        input.focus()

    def compose(self) -> ComposeResult:
        yield Input(id="chat-input-box")


class QuitScreen(Screen):
    """Screen with a dialog to quit."""

    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Are you sure you want to quit?", id="question"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
        else:
            self.app.pop_screen()


class SettingsScreen(Screen):
    """Screen with a dialog to display settings."""

    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    def compose(self) -> ComposeResult:
        self.widget_user_name = Input(APP_CONFIG.get_user_name())
        self.widget_user_bio = TextArea(APP_CONFIG.get_user_bio())
        yield Container(
            Grid(Label("Configuration", classes="heading"), id="settings-screen-header"),
            Grid(
                Container(Label("User", classes="form-label"), self.widget_user_name),
                Container(Label("Bio", classes="form-label"), self.widget_user_bio),
                id="settings-screen-contents",
            ),
            Grid(
                Button("Save", variant="primary", id="save-settings"),
                Button("Close", variant="error", id="close-settings"),
                id="settings-screen-footer",
            ),
            id="settings-screen",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-settings":
            self.app.pop_screen()
        elif event.button.id == "save-settings":
            new_user_name = self.widget_user_name.value
            new_user_bio = self.widget_user_bio.text

            APP_CONFIG.update_configuration(user_name=new_user_name, user_bio=new_user_bio)

            self.app.pop_screen()


class ChatScreen(Screen):
    """A screen that displays a chat history"""

    root_msg_id = 0

    def compose(self) -> ComposeResult:
        history = json.dumps(fetch_chat_history(self.root_msg_id), indent=2)
        yield Grid(
            ScrollableContainer(
                Static(f"Here is the history for {self.root_msg_id}\n{history}", id="sub-chat-history-contents")
            ),
            Button("Cancel", variant="primary", id="cancel"),
            id="sub-chat-history",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            self.app.pop_screen()


class TinyRA(App):
    """
    A Textual app to display chat history.

    The app is composed of the following widgets:
    - Header
    - DirectoryTreeContainer
    - ChatDisplay
    - SkillsDisplayContainer
    - ChatInput
    - Footer

    The app also has the following key bindings:
    - ctrl+t: toggle dark mode
    - ctrl+z: quit the app
    - ctrl+r: retry last user message
    - ctrl+g: memorize the autogen message
    """

    BINDINGS = [
        ("ctrl+c", "request_quit", "Quit"),
        ("ctrl+s", "request_settings", "Settings"),
    ]

    CSS_PATH = "tui.css"

    TITLE = "TinyRA"
    SUB_TITLE = "A minimalistic, long-lived research assistant"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Grid(
            Header(show_clock=True),
            DirectoryTreeContainer(id="directory-tree"),
            ChatDisplay(id="chat-history"),
            SkillsDisplayContainer(id="skills"),
            # Static(id="status"),
            ChatInput(id="chat-input"),
            Footer(),
            id="main-grid",
        )

    def on_mount(self) -> None:
        self.install_screen(QuitScreen(), name="quit-screen")
        self.install_screen(SettingsScreen(), name="settings-screen")

    def action_request_quit(self) -> None:
        # check if there is already a quit screen
        # check if a quit screen is already on the stack
        self.push_screen("quit-screen")

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_request_settings(self) -> None:
        self.push_screen("settings-screen")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Called when the user click a file in the directory tree."""
        event.stop()
        try:
            # open the file using the default app
            logging.info(f"Opening file {event.path}")
            # check if the app is running in a codespace
            if os.environ.get("CODESPACES"):
                os.system(f"code {event.path}")
            else:
                # open the file using the default app
                os.system(f"open '{event.path}'")
        except Exception:
            # TODO: Not implemented
            pass
        else:
            # TODO: Not implemented
            pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = self.query_one("#chat-input-box", Input).value.strip()
        self.query_one(Input).value = ""
        self.handle_input(user_input)

    def on_reactive_assistant_message_selected(self, event: ReactiveAssistantMessage.Selected) -> None:
        """Called when a reactive assistant message is selected."""
        new_chat_screen = ChatScreen()
        new_chat_screen.root_msg_id = event.msg_id
        self.push_screen(new_chat_screen)

    @work()
    async def handle_input(self, user_input: str) -> None:
        id = insert_chat_message("user", user_input, root_id=0)
        self.generate_response(msg_idx=id)

    @work()
    async def generate_response(self, msg_idx: int, limit_history=None) -> None:
        """
        Solve the autogen quick start.

        Returns:
            The solution to the autogen quick start.
        """
        # status_widget = self.query_one("#status", Static)
        # status_widget.update(f"Starting autogen in a worker process for {msg_idx}...")

        # fetch the relevant chat history
        chat_history = fetch_chat_history()
        task = chat_history[msg_idx]["content"]
        chat_history = chat_history[0:msg_idx]

        def terminate_on_consecutive_empty(recipient, messages, sender, **kwargs):
            # check the contents of the last N messages
            # if all empty, terminate
            all_empty = True
            last_n = 2
            for message in reversed(messages):
                if last_n == 0:
                    break
                if message["role"] == "user":
                    last_n -= 1
                    if len(message["content"]) > 0:
                        all_empty = False
                        break
            if all_empty:
                return True, "TERMINATE"
            return False, None

        def summarize(text):
            if len(text) > 100:
                return text[:100] + "..."
            return text

        async def post_update_to_main(recipient, messages, sender, **kwargs):
            last_assistant_message = None
            for msg in reversed(messages):
                if msg["role"] == "assistant":
                    last_assistant_message = msg
                    break

            # update_message = "Computing response..."
            if last_assistant_message:
                summary = summarize(last_assistant_message["content"])
                update_message = f"{summary}..."
                await a_insert_chat_message("info", update_message, root_id=0, id=msg_idx + 1)
            else:
                num_messages = len(messages)
                await a_insert_chat_message("info", f"Num messages...{num_messages}", root_id=0, id=msg_idx + 1)
            return False, None

        async def post_last_user_msg_to_chat_history(recipient, messages, sender, **kwargs):
            last_message = messages[-1]
            await a_insert_chat_message("user", last_message["content"], root_id=msg_idx + 1)
            return False, None

        async def post_last_assistant_msg_to_chat_history(recipient, messages, sender, **kwargs):
            last_message = messages[-1]
            await a_insert_chat_message("assistant", last_message["content"], root_id=msg_idx + 1)
            return False, None

        assistant = AssistantAgent(
            "assistant",
            llm_config=LLM_CONFIG,
            system_message=APP_CONFIG.get_assistant_system_message(),
        )
        user = UserProxyAgent(
            "user",
            code_execution_config={"work_dir": os.path.join(APP_CONFIG.get_data_path(), "work_dir")},
            human_input_mode="NEVER",
            is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
        )
        assistant.register_reply(Agent, AssistantAgent.a_generate_oai_reply, 3)
        # assistant.register_reply(Agent, AssistantAgent.a_get_human_input, 3)
        assistant.register_reply(Agent, terminate_on_consecutive_empty, 2)
        assistant.register_reply(Agent, post_update_to_main, 1)
        assistant.register_reply(Agent, post_last_user_msg_to_chat_history, 0)
        user.register_reply(Agent, post_last_assistant_msg_to_chat_history, 0)

        for msg in chat_history:
            if msg["role"] == "user":
                await user.a_send(msg["content"], assistant, request_reply=False, silent=True)
            else:
                await assistant.a_send(msg["content"], user, request_reply=False, silent=True)

        await user.a_initiate_chat(assistant, message=task, clear_history=False)
        await user.a_send(
            f"""Based on the results in above conversation, create a response for the user.
While computing the response, remember that this conversation was your inner mono-logue. The user does not need to know every detail of the conversation.
All they want to see is the appropriate result for their task (repeated below) in a manner that would be most useful.
The task was: {task}

There is no need to use the word TERMINATE in this response.
            """,
            assistant,
            request_reply=False,
            silent=True,
        )
        response = await assistant.a_generate_reply(assistant.chat_messages[user], user)
        await assistant.a_send(response, user, request_reply=False, silent=True)

        response = assistant.chat_messages[user][-1]["content"]

        await a_insert_chat_message("assistant", response, root_id=0, id=msg_idx + 1)


def run_app() -> None:
    """
    Run the TinyRA app.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset chat history")
    parser.add_argument("--reset-all", action="store_true", help="Reset chat history and delete data path")
    args = parser.parse_args()

    if args.reset_all:
        print(f"Warning: Resetting chat history and deleting data path {APP_CONFIG.get_data_path()}")
        print("Press enter to continue or Ctrl+C to cancel.")
        input()
        if os.path.exists(APP_CONFIG.get_database_path()):
            os.remove(APP_CONFIG.get_database_path())
        if os.path.exists(APP_CONFIG.get_data_path()):
            shutil.rmtree(APP_CONFIG.get_data_path())
        exit()

    if args.reset:
        print(f"Warning: Resetting chat history. This will delete all chat history in {APP_CONFIG.get_database_path()}")
        print("Press enter to continue or Ctrl+C to cancel.")
        input()
        if os.path.exists(APP_CONFIG.get_database_path()):
            os.remove(APP_CONFIG.get_database_path())
        exit()

    app = TinyRA()
    app.run()


if __name__ == "__main__":
    run_app()
