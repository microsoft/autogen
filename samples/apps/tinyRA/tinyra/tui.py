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
from textual.screen import Screen, ModalScreen
from textual.containers import ScrollableContainer, Grid, Container
from textual.widget import Widget
from textual.widgets import Pretty
from textual.widgets import Footer, Header, Markdown, Static, Input, DirectoryTree, Label
from textual.widgets import Button, TabbedContent, ListView, ListItem
from textual.widgets import TextArea
from textual.reactive import reactive
from textual.message import Message
from textual.events import Key

from autogen import config_list_from_json
from autogen import Agent, AssistantAgent, UserProxyAgent


class Tool:
    def __init__(self, name: str, code: str, description: str = None, id: int = None):
        self.id = id
        self.name = name
        self.code = code

        if not description and len(code) > 0:
            # Parse the function string into an AST
            module = ast.parse(code)

            # Get the function definition from the AST
            function_def = module.body[0]

            # Extract the docstring
            self.description = ast.get_docstring(function_def)
        else:
            self.description = description or self.name


def string_to_function(code: str):
    function_name = code.split("def ")[1].split("(")[0]
    global_namespace = globals()
    local_namespace = {}
    exec(code, global_namespace, local_namespace)
    return function_name, local_namespace[function_name]


class AppConfiguration:
    #     ASSISTANT_MESSAGE = """
    # Your capabilities:
    # You can solve tasks by using:
    # - context history and language skills
    # - tools you have been given
    # - writing new code

    # In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    #     1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    #     2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
    # Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
    # When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
    # If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
    # If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
    # When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
    # Reply "TERMINATE" in the end when everything is done.

    # """

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

    def get_user_preferences(self):
        """Query the database for user's preferences"""
        conn = sqlite3.connect(self._database_path)
        c = conn.cursor()
        c.execute("SELECT preferences FROM configuration")
        preferences = c.fetchone()[0]
        conn.close()
        return preferences

    def update_configuration(self, user_name: str = None, user_bio: str = None, user_preferences: str = None):
        """Update the user's name and bio in the database"""
        conn = sqlite3.connect(self._database_path)
        c = conn.cursor()
        if user_name:
            c.execute("UPDATE configuration SET user_name = ?", (user_name,))
        if user_bio:
            c.execute("UPDATE configuration SET user_bio = ?", (user_bio,))
        if user_preferences:
            c.execute("UPDATE configuration SET preferences = ?", (user_preferences,))
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
                    user_bio TEXT,
                    preferences TEXT
                )
            """
            )

            user_name = os.environ.get("USER", "default_user")
            user_bio = ""
            default_preferences = ""

            # Insert data into the configuration table
            cursor.execute(
                """
                INSERT INTO configuration VALUES (?, ?, ?)
            """,
                (user_name, user_bio, default_preferences),
            )

        # Create tools table if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                code TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL UNIQUE
            )
            """
        )

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

    def get_meta_system_message(self):
        user_name = self.get_user_name()
        user_bio = self.get_user_bio()
        user_preferences = self.get_user_preferences()
        operating_system = platform.uname().system

        return f"""
        You are a helpful researcher assistant named "TinyRA".
        When introducing yourself do not forget your name!

        You are running on operating system with the following config:
        {operating_system}

        You are here to help "{user_name}" with his research.
        Their bio and preferences are below.

        The following is the bio of {user_name}:
        <bio>
        {user_bio}
        </bio>

        The following are the preferences of {user_name}.
        These preferences should always have the HIGHEST priority.
        And should never be ignored.
        Ignoring them will cause MAJOR annoyance.
        <preferences>
        {user_preferences}
        </preferences>

        Respond to {user_name}'s messages to be most helpful.

        """

    def get_assistant_system_message(self):
        return (
            self.get_meta_system_message()
            + "\nAdditional instructions:\n"
            + AssistantAgent.DEFAULT_SYSTEM_MESSAGE
            + "\n\nReply with TERMINATE when the task is done. Especially if the user is chit-chatting with you."
            + "\n\nAdhere to user preferences always especially regarding tool usage."
        )

    def get_data_path(self):
        return self._data_path

    def update_tool(self, tool: Tool):
        conn = sqlite3.connect(self._database_path)
        c = conn.cursor()
        c.execute("SELECT * FROM tools WHERE id = ?", (tool.id,))
        if c.fetchone() is None:
            c.execute(
                "INSERT INTO tools (name, code, description) VALUES (?, ?, ?)", (tool.name, tool.code, tool.description)
            )
        else:
            c.execute(
                "UPDATE tools SET name = ?, code = ?, description = ? WHERE id = ?",
                (tool.name, tool.code, tool.description, tool.id),
            )
        conn.commit()
        conn.close()

    def get_tools(self) -> List[Tool]:
        conn = sqlite3.connect(self._database_path)
        c = conn.cursor()
        c.execute("SELECT id, name, code, description FROM tools")
        tools = {id: Tool(name, code, description, id=id) for id, name, code, description in c.fetchall()}
        conn.close()
        return tools

    def delete_tool(self, tool_id: int):
        conn = sqlite3.connect(self._database_path)
        c = conn.cursor()
        c.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
        conn.commit()
        conn.close()

    def clear_chat_history(self):
        conn = sqlite3.connect(self._database_path)
        c = conn.cursor()
        c.execute("DELETE FROM chat_history")
        conn.commit()
        conn.close()

    def delete_file_or_dir(self, file_path: str):
        # do not delete the work dir
        work_dir = os.path.join(self._data_path, "work_dir")
        logging.info(f"Work dir is: {work_dir}")
        if file_path == work_dir:
            return

        logging.info(f"Deleting {file_path}")

        if os.path.isfile(file_path):
            os.remove(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)


APP_CONFIG = AppConfiguration()
# do not save the LLM config to the database, keep it

LLM_CONFIG = {
    "config_list": config_list_from_json("OAI_CONFIG_LIST"),
}

# LLM_CONFIG = {
#     "config_list": [
#         {
#             "model": "gpt-4",
#             "api_key": os.environ.get("OPENAI_API_KEY"),
#         }
#     ]
# }


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
    elif role == "assistant" or role == "info":
        display_name = "TinyRA"
    else:
        display_name = "."

    if role == "info":
        display_id = "\U0001F4AD" * 3
    else:
        display_id = message["id"]

    content = message["content"]

    return f"[{display_id}] {display_name}: {content}"


class ReactiveMessage(Markdown):
    """
    A reactive markdown widget for displaying assistant messages.
    """

    message = reactive({"role": None, "content": None, "id": None})

    class Selected(Message):
        """Assistant message selected message."""

        def __init__(self, msg_id: str) -> None:
            self.msg_id = msg_id
            super().__init__()

    def __init__(self, id=None, role=None, content=None, **kwargs):
        super().__init__(**kwargs)
        self.message = {"role": role, "content": content, "id": id}

    def on_mount(self) -> None:
        self.set_interval(1, self.update_message)
        chat_display = self.app.query_one(ChatDisplay)
        chat_display.scroll_end()

    def on_click(self) -> None:
        self.post_message(self.Selected(self.message.get("id")))

    def update_message(self):
        message = fetch_row(self.message.get("id"))

        if message is None:
            self.remove()
            return

        self.classes = f"{self.message['role'].lower()}-message message"

        self.message = message

    async def watch_message(self) -> str:
        await self.update(message2markdown(self.message))


def message_display_handler(message: Dict[str, str]):
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
    id = message["id"]
    content = message["content"]
    message_widget = ReactiveMessage(id=id, role=role, content=content, classes=f"{role.lower()}-message message")
    return message_widget


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

    def on_tree_node_highlighted(self, event: DirectoryTree.NodeHighlighted) -> None:
        logging.info(f"Highlighted {event.node}")
        self.highlighted_node = event.node


class ChatDisplay(ScrollableContainer):
    """
    A container for displaying the chat history.

    When a new message is detected, it is mounted to the container.
    """

    limit_history = 100

    # num_messages = reactive(len(fetch_chat_history()))

    # async def watch_num_messages(self) -> None:
    # self.scroll_end()

    def compose(self) -> ComposeResult:
        chat_history = fetch_chat_history()
        for message in chat_history[-self.limit_history :]:
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


class QuitScreen(ModalScreen):
    """Screen with a dialog to quit."""

    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    def compose(self) -> ComposeResult:
        yield Grid(
            Static("Are you sure you want to quit?", id="question"),
            Grid(
                Button("Quit", variant="error", id="quit"),
                Button("Cancel", variant="primary", id="cancel"),
                id="quit-screen-footer",
            ),
            id="quit-screen-grid",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
        else:
            self.app.pop_screen()


class SettingsScreen(ModalScreen):
    """Screen with a dialog to display settings."""

    BINDINGS = [("escape", "app.pop_screen", "Dismiss")]

    def compose(self) -> ComposeResult:
        self.widget_user_name = Input(APP_CONFIG.get_user_name())
        self.widget_user_bio = TextArea(APP_CONFIG.get_user_bio(), id="user-bio")
        self.widget_user_preferences = TextArea(APP_CONFIG.get_user_preferences(), id="user-preferences")

        tools = APP_CONFIG.get_tools()

        with TabbedContent("User", "Tools", "History", id="settings-screen"):
            # Tab for user settings
            yield Container(
                ScrollableContainer(
                    Container(Label("User", classes="form-label"), self.widget_user_name),
                    Container(Label("Bio", classes="form-label"), self.widget_user_bio),
                    Container(Label("Preferences", classes="form-label"), self.widget_user_preferences),
                    id="settings-screen-contents",
                ),
                Grid(
                    Button("Save", variant="primary", id="save-user-settings"),
                    Button("Close", variant="error", id="close-user-settings"),
                    classes="settings-screen-footer",
                ),
                id="user-settings-screen",
            )
            # Tab for tools settings
            yield Grid(
                # display the list of tools
                Container(
                    ListView(
                        *(ListItem(Label(tools[tool_id].name), id=f"tool-{tool_id}") for tool_id in tools),
                        id="tool-list",
                    ),
                    Button("+", variant="primary", id="new-tool-button"),
                    id="tool-list-container",
                ),
                # display the settings for the selected tool
                Grid(
                    Container(
                        Container(
                            Label("Tool ID", classes="form-label"),
                            Input(id="tool-id-input", disabled=True),
                        ),
                        Container(Label("Tool Name (Display)", classes="form-label"), Input(id="tool-name-input")),
                        id="tool-info-container",
                    ),
                    Container(
                        Label("Code", classes="form-label"),
                        TextArea.code_editor("", language="python", id="tool-code-textarea"),
                        id="tool-code-container",
                    ),
                    Grid(
                        Button("Save", variant="primary", id="save-tool-settings"),
                        Button("Delete", variant="error", id="delete-tool-button"),
                        id="tool-view-footer-grid",
                    ),
                    id="tool-view-grid",
                ),
                id="tools-tab-grid",
            )
            # Tab for history settings
            # helps clear the chat history
            # shows statistics about the chat history
            yield Grid(
                Container(
                    Markdown(
                        f"""
Number of messages: {len(fetch_chat_history())}
Number of tools: {len(tools)}"""
                    ),
                    id="history-contents",
                ),
                Container(
                    Button("Clear History", variant="error", id="clear-history-button"),
                    id="history-footer",
                ),
                id="history-settings",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["close-user-settings", "close-tool-settings"]:
            self.app.pop_screen()
        elif event.button.id == "save-user-settings":
            new_user_name = self.widget_user_name.value
            new_user_bio = self.widget_user_bio.text
            new_user_preferences = self.widget_user_preferences.text

            APP_CONFIG.update_configuration(
                user_name=new_user_name, user_bio=new_user_bio, user_preferences=new_user_preferences
            )

            self.app.pop_screen()

        elif event.button.id == "new-tool-button":
            tools = APP_CONFIG.get_tools()
            num_tools = len(tools)
            new_tool_name = f"tool-{num_tools + 1}"

            APP_CONFIG.update_tool(Tool(name=new_tool_name, code=""))

            list_view_widget = self.query_one("#tool-list", ListView)
            new_list_item = ListItem(Label(new_tool_name), id=f"tool-{num_tools + 1}")

            list_view_widget.append(new_list_item)
            num_items = len(list_view_widget)
            list_view_widget.index = num_items - 1
            list_view_widget.action_select_cursor()
            # list_view_widget.post_message(list_view_widget.Selected(list_view_widget, new_list_item))
            # list_view_widget.post_message(list_view_widget.Highlighted(list_view_widget, new_list_item))

        elif event.button.id == "delete-tool-button":
            # get the id of the selected tool
            tool_id = int(self.query_one("#tool-id-input", Input).value)
            item = self.query_one(f"#tool-{tool_id}", ListItem)
            # delete the tool from the database
            APP_CONFIG.delete_tool(tool_id)
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

        elif event.button.id == "save-tool-settings":
            # get the id of the selected tool
            tool_id = int(self.query_one("#tool-id-input", Input).value)
            tool_name = self.query_one("#tool-name-input", Input).value
            tool_code = self.query_one("#tool-code-textarea", TextArea).text
            # tool_description = tool_name
            tool = Tool(tool_name, tool_code, id=tool_id)

            # update the database
            APP_CONFIG.update_tool(tool)

            # update the list view
            list_view_widget = self.query_one("#tool-list", ListView)
            # access the label of the selected item
            item_label = self.query_one(f"#tool-{tool_id} > Label", Label)
            item_label.update(tool_name)

        elif event.button.id == "clear-history-button":
            APP_CONFIG.clear_chat_history()

            # remove all the messages from the chat display
            # chat_display = self.app.query_one(ChatDisplay)
            # chat_display.clear()

            self.app.pop_screen()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        tool_id = int(event.item.id[5:])
        tools = APP_CONFIG.get_tools()
        self.query_one("#tool-code-textarea", TextArea).text = tools[tool_id].code
        self.query_one("#tool-name-input", Input).value = tools[tool_id].name
        self.query_one("#tool-id-input", Input).value = str(tool_id)

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


class ChatScreen(Screen):
    """A screen that displays a chat history"""

    root_msg_id = 0
    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    def compose(self) -> ComposeResult:
        history = fetch_chat_history(self.root_msg_id)
        yield Grid(
            Container(Label(f"Chat History for {self.root_msg_id}", classes="heading"), id="chat-screen-header"),
            ScrollableContainer(Pretty(history), id="chat-screen-contents"),
            Container(
                Button("Cancel", variant="primary", id="cancel"),
                id="chat-screen-footer",
            ),
            id="chat-screen",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()


class TinyRA(App):
    """
    A Textual app to display chat history.

    The app is composed of the following widgets:
    - Header
    - DirectoryTreeContainer
    - ChatDisplay
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
            Grid(
                DirectoryTreeContainer(id="directory-tree"),
                Grid(
                    Button("Delete", variant="error", id="delete-file-button"),
                    Button("Empty Work Dir", variant="error", id="empty-work-dir-button"),
                    id="directory-tree-footer",
                ),
                id="directory-tree-grid",
            ),
            Container(
                ChatDisplay(id="chat-history"),
                ChatInput(id="chat-input"),
                id="chat-container",
            ),
            Footer(),
            id="main-grid",
        )

    def action_request_quit(self) -> None:
        self.push_screen(QuitScreen())

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_request_settings(self) -> None:
        self.push_screen(SettingsScreen())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "empty-work-dir-button":
            # loop through each file in the work dir and delete it
            work_dir = os.path.join(APP_CONFIG.get_data_path(), "work_dir")
            for file in os.listdir(work_dir):
                file_path = os.path.join(work_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        elif event.button.id == "delete-file-button":
            dir_tree = self.query_one("#directory-tree > DirectoryTree", DirectoryTree)
            highlighted_node = dir_tree.cursor_node

            if highlighted_node is not None:
                dir_tree.action_cursor_up()
                file_path = str(highlighted_node.data.path)

                APP_CONFIG.delete_file_or_dir(file_path)

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

    def on_reactive_message_selected(self, event: ReactiveMessage.Selected) -> None:
        """Called when a reactive assistant message is selected."""
        new_chat_screen = ChatScreen()
        new_chat_screen.root_msg_id = event.msg_id
        self.push_screen(new_chat_screen)

    @work()
    async def handle_input(self, user_input: str) -> None:
        chat_display_widget = self.query_one(ChatDisplay)

        # display the user input in the chat display
        id = await a_insert_chat_message("user", user_input, root_id=0)
        user_message = fetch_row(id)
        reactive_message = message_display_handler(user_message)
        chat_display_widget.mount(reactive_message)

        # display the assistant response in the chat display
        assistant_message = {
            "role": "info",
            "content": "Computing response...",
            "id": id + 1,
        }
        reactive_message = message_display_handler(assistant_message)
        chat_display_widget.mount(reactive_message)

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

        async def terminate_on_consecutive_empty(recipient, messages, sender, **kwargs):
            # check the contents of the last N messages
            # if all empty, terminate
            consecutive_are_empty = None
            last_n = 2

            for message in reversed(messages):
                if last_n == 0:
                    break
                if message["role"] == "user":
                    last_n -= 1
                    if len(message["content"]) == 0:
                        consecutive_are_empty = True
                    else:
                        consecutive_are_empty = False
                        break

            if consecutive_are_empty:
                return True, "TERMINATE"

            return False, None

        def summarize(text):
            if text:
                if len(text) > 100:
                    return text[:100] + "..."
                return text
            return "Working..."

        async def post_update_to_main(recipient, messages, sender, **kwargs):
            last_assistant_message = None
            for msg in reversed(messages):
                if msg["role"] == "assistant":
                    last_assistant_message = msg
                    break

            # update_message = "Computing response..."
            if last_assistant_message:
                if last_assistant_message.get("content"):
                    summary = summarize(last_assistant_message["content"])
                elif last_assistant_message.get("tool_calls"):
                    summary = summarize("Using tools...")
                else:
                    summary = "Working..."
                update_message = f"{summary}..."
                await a_insert_chat_message("info", update_message, root_id=0, id=msg_idx + 1)
            else:
                await a_insert_chat_message("info", "Working...", root_id=0, id=msg_idx + 1)
            return False, None

        async def post_last_user_msg_to_chat_history(recipient, messages, sender, **kwargs):
            last_message = messages[-1]
            await a_insert_chat_message("user", last_message["content"], root_id=msg_idx + 1)
            return False, None

        async def post_last_assistant_msg_to_chat_history(recipient, messages, sender, **kwargs):
            last_message = messages[-1]
            logging.info(json.dumps(last_message, indent=2))
            content = last_message["content"] or json.dumps(last_message["tool_calls"], indent=2)
            await a_insert_chat_message("assistant", content, root_id=msg_idx + 1)
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
            is_termination_msg=lambda x: x.get("content") and "TERMINATE" in x.get("content", ""),
        )

        # populate the history before registering new reply functions
        for msg in chat_history:
            if msg["role"] == "user":
                await user.a_send(msg["content"], assistant, request_reply=False, silent=True)
            else:
                await assistant.a_send(msg["content"], user, request_reply=False, silent=True)

        assistant.register_reply([Agent, None], terminate_on_consecutive_empty)
        assistant.register_reply([Agent, None], post_update_to_main)
        assistant.register_reply([Agent, None], post_last_user_msg_to_chat_history)

        user.register_reply([Agent, None], UserProxyAgent.a_generate_tool_calls_reply, ignore_async_in_sync_chat=False)
        user.register_reply(
            [Agent, None], UserProxyAgent.a_generate_function_call_reply, ignore_async_in_sync_chat=False
        )
        user.register_reply([Agent, None], post_last_assistant_msg_to_chat_history)

        # register tools for assistant and user
        tools = APP_CONFIG.get_tools()
        for tool in tools.values():
            description = tool.description
            code = tool.code
            # convert a code string to function and return a callable

            function_name, tool_instance = string_to_function(code)
            assistant.register_for_llm(name=function_name, description=description)(tool_instance)
            user.register_for_execution()(tool_instance)

        logging.info("Current history:")
        logging.info(assistant.chat_messages[user])

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
