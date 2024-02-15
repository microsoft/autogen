import os
import asyncio
import ast
import configparser
import platform
import json
import logging
import argparse
import shutil
import subprocess

from typing import List, Dict

from textual import work
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Grid
from textual.events import Mount
from textual.widgets import Footer, Header, Markdown, Static, Input, DirectoryTree, Label
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button

import sqlite3
import tiktoken
import aiosqlite

from autogen import config_list_from_json
from autogen import Agent, AssistantAgent, UserProxyAgent


# get the path of the current script
user_home = os.path.expanduser("~")
DATA_PATH = os.path.join(user_home, ".tinyra")
if not os.path.exists(DATA_PATH):
    os.mkdir(DATA_PATH)

logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(DATA_PATH, "tinyra.log"),
    filemode="w",
    format="%(asctime)-15s %(message)s",
)


MODEL = "gpt-4"
OS_USER_NAME = os.environ.get("USER", None)
USER_NAME = os.environ.get("TINYRA_USER", OS_USER_NAME)
if USER_NAME is None:
    print("Please set the TINYRA_USER environment variable with your name, e.g., export TINYRA_USER=Bob")
    exit(1)
CONFIG = configparser.ConfigParser()
CHATDB = os.path.join(DATA_PATH, "chat_history.db")


def init_database() -> None:
    """
    Initialize the chat history database.
    """
    conn = sqlite3.connect(CHATDB)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


USER_PROFILE_TEXT = ""
OPERATING_SYSTEM = platform.system()
UTILS_FILE = os.path.join(DATA_PATH, "agent_utils.py")
if not os.path.exists(UTILS_FILE):
    with open(UTILS_FILE, "w") as f:
        f.write("")
CONFIG_LIST = config_list_from_json("OAI_CONFIG_LIST")
LLM_CONFIG = config_list_from_json("OAI_CONFIG_LIST")[0]
LLM_CONFIG["seed"] = 42

META_SYSTEM_MESSAGE = f"""
You are a helpful researcher assistant named "TinyRA".
When introducing yourself do not forget your name!

You are running on {OPERATING_SYSTEM} operating system.
You are here to help "{USER_NAME}" with his research.

The following is the bio of {USER_NAME}:
<bio>
{USER_PROFILE_TEXT}
</bio>

Respond to {USER_NAME}'s messages to be most helpful.

"""

ASSISTANT_SYSTEM_MESSAGE = (
    META_SYSTEM_MESSAGE
    + "\nAdditional instructions\n"
    + AssistantAgent.DEFAULT_SYSTEM_MESSAGE
    + "\n\nDon't forget to reply with TERMINATE when the task is done or you get stuck in introductory, empty message, or apology loop"
)

WORK_DIR = os.path.join(DATA_PATH, "work_dir")
if not os.path.exists(WORK_DIR):
    os.makedirs(WORK_DIR)

if not os.path.exists(CHATDB):
    init_database()


def fetch_chat_history() -> List[Dict[str, str]]:
    """
    Fetch the chat history from the database.

    Returns:
        A list of chat messages.
    """
    conn = sqlite3.connect(CHATDB)
    c = conn.cursor()
    c.execute("SELECT id, role, content FROM chat_history")
    chat_history = [{"id": id, "role": role, "content": content} for id, role, content in c.fetchall()]
    conn.close()
    return chat_history


def fetch_row(id: int) -> Dict[str, str]:
    """
    Fetch a single row from the database.

    Args:
        id: the id of the row to fetch

    Returns:
        A single row from the database.
    """
    conn = sqlite3.connect(CHATDB)
    c = conn.cursor()
    c.execute("SELECT role, content FROM chat_history WHERE id = ?", (id,))
    row = [{"role": role, "content": content, "id": id} for role, content in c.fetchall()]
    conn.close()
    return row[0]


def insert_chat_message(role: str, content: str, row_id: int = None) -> int:
    """
    Insert a chat message into the database.

    Args:
        role: the role of the message
        content: the content of the message
        row_id: the id of the row to update. If None, a new row is inserted.

    Returns:
        The id of the inserted (or modified) row.
    """
    try:
        with sqlite3.connect(CHATDB) as conn:
            c = conn.cursor()
            if row_id is None:
                data = (role, content)
                c.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", data)
                row_id = c.lastrowid
                conn.commit()
                return row_id
            else:
                c.execute("SELECT * FROM chat_history WHERE id = ?", (row_id,))
                if c.fetchone() is None:
                    data = (role, content)
                    c.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", data)
                    row_id = c.lastrowid
                    conn.commit()
                    return row_id
                else:
                    data = (role, content, row_id)
                    c.execute("UPDATE chat_history SET role = ?, content = ? WHERE id = ?", data)
                    conn.commit()
                    return row_id
    except sqlite3.Error as e:
        print(f"Error inserting or updating chat message: {e}")


async def a_insert_chat_message(role: str, content: str, row_id: int = None) -> int:
    """
    Insert a chat message into the database.

    Args:
        role: the role of the message
        content: the content of the message
        row_id: the id of the row to update. If None, a new row is inserted.

    Returns:
        The id of the inserted (or modified) row.
    """
    try:
        async with aiosqlite.connect(CHATDB) as conn:
            c = await conn.cursor()
            if row_id is None:
                data = (role, content)
                await c.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", data)
                row_id = c.lastrowid
                await conn.commit()
                return row_id
            else:
                await c.execute("SELECT * FROM chat_history WHERE id = ?", (row_id,))
                if await c.fetchone() is None:
                    data = (role, content)
                    await c.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", data)
                    row_id = c.lastrowid
                    await conn.commit()
                    return row_id
                else:
                    data = (role, content, row_id)
                    await c.execute("UPDATE chat_history SET role = ?, content = ? WHERE id = ?", data)
                    await conn.commit()
                    return row_id
    except aiosqlite.Error as e:
        print(f"Error inserting or updating chat message: {e}")


def num_tokens_from_messages(messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo-0301") -> int:
    """
    Returns the number of tokens used by a list of messages.

    Args:
        messages: a list of messages
        model: the model to use for encoding

    Returns:
        The number of tokens used by the messages.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if "gpt-3.5" in model or "gpt-4" in model:  # note: future models may deviate from this
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not presently implemented for model {model}. Currently supports OpenAI models with prefix "gpt-3.5" and "gpt4" only."""
        )


def truncate_messages(
    messages: List[Dict[str, str]], model: str, minimum_response_tokens: int = 1000
) -> List[Dict[str, str]]:
    """
    Truncates messages to fit within the maximum context length of a given model.

    Args:
        messages: a list of messages
        model: the model to truncate for
        minimum_response_tokens: the minimum number of tokens to leave for the response

    Returns:
        A list of messages that fit within the maximum context length of the model.
    """
    max_context_tokens = None
    if model == "gpt-4-32k":
        max_context_tokens = 32000
    elif model == "gpt-4":
        max_context_tokens = 32000
    elif model == "gpt-3.5-turbo":
        max_context_tokens = 4000
    elif model == "gpt-3.5-turbo-16k":
        max_context_tokens = 16000
    else:
        raise ValueError(f"Unsupported model: {model}")

    new_messages = None
    start_idx = 1
    while True:
        new_messages = [messages[0]] + messages[start_idx:]
        prompt_tokens = num_tokens_from_messages(new_messages)

        if prompt_tokens <= max_context_tokens - minimum_response_tokens:
            break
        else:
            start_idx += 1
    return new_messages


async def ask_gpt(messages: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Sends a list of messages to the GPT model and returns the response.

    Args:
        messages (list): A list of dictionaries representing the chat history. Each dictionary should have "role" and "content" keys.

    Returns:
        dict: The response from the GPT model with "role" and "content" keys.
    """
    # filer only role and content keys from the chat history
    messages = [{k: v for k, v in m.items() if k in ["role", "content"]} for m in messages]
    messages = [m for m in messages if m["role"] in ["assistant", "user"]]

    assistant = AssistantAgent(
        "assistant",
        system_message=ASSISTANT_SYSTEM_MESSAGE,
        llm_config=LLM_CONFIG,
    )
    user = UserProxyAgent("user", code_execution_config=False)

    logging.debug("Messages", messages)
    for i, message in enumerate(messages):
        if message["role"] == "assistant":
            await assistant.a_send(message, user, request_reply=False)
        elif message["role"] == "user":
            is_last_user_msg = False
            if i == len(messages) - 1:
                is_last_user_msg = True
            await user.a_send(message, assistant, request_reply=is_last_user_msg)

    response = assistant.chat_messages[user][-1]
    logging.debug("Response", response)
    return response


async def chat_completion_wrapper(row_id: int, messages: List[Dict[str, str]]) -> Dict[str, str]:
    """
    A wrapper around ask_gpt() that handles errors and retries.

    Args:
        row_id: the id of the row to update
        messages: a list of messages

    Returns:
        The response from the GPT model with "role" and "content" keys.
    """
    while True:
        try:
            response = await ask_gpt(messages)
            response["id"] = row_id
            return response
        except Exception as e:
            insert_chat_message("error", f"{e}", row_id)
            return None


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


async def handle_autogen(msg_id: int) -> None:
    """
    Handle the autogen message with the given msg_id.

    Args:
        msg_id (int): The ID of the message.

    Raises:
        subprocess.CalledProcessError: If the subprocess execution fails.

    """

    script_path = os.path.join(os.path.dirname(__file__), "run_tinyra.sh")
    subprocess.run(["bash", script_path, "tab", str(msg_id)], check=True)


async def get_standalone_func(content: str) -> str:
    """
    Given a message, extract the python function and return it as a string.

    Args:
        content: the message content

    Returns:
        A string representing the python function.
    """
    messages = [
        {
            "role": "user",
            "content": f"""
        Extract and return a python function from the following text.
        All import statements should be inside the function definitions.
        the function should have a doc string using triple quotes.
        Return the function as plain text without any code blocks.

        {content}
        """,
        }
    ]
    row_id = insert_chat_message("info", "Generating code...")
    response = await chat_completion_wrapper(row_id=row_id, messages=messages)

    return response["content"]


def is_cp_format(string: str) -> bool:
    """
    Check if the string is in the cp format.

    Args:
        string: the string to check

    Returns:
        True if the string is in the cp format, False otherwise.
    """
    import re

    pattern = r"cp \d+$"
    return bool(re.match(pattern, string))


async def handle_user_input() -> None:
    """
    Handle the user input.


    This function is called when the user submits a message.

    It handles several cases.
    - if the message is in the cp format and if yes,
    it copies the message with the given id to the clipboard.

    - if the message is not in the cp format, it checks if the message
    is an autogen message and if yes, it generates the code for the message.

    - if the message is not an autogen message, it checks if the message
    requires autogen and if yes, it generates the code for the message.

    - if the message does not require autogen, it generates a direct response
    for the message.

    The response is generated by sending the messages to the GPT model.

    It also handles the @memorize command and inserts the function to the
    end of the file agent_utils.py.

    When a response is generated, it is inserted into the chat history.
    """

    messages = fetch_chat_history()

    # find the last user message
    last_user_message = None
    last_user_message_id = None
    for message in reversed(messages):
        if message["role"] == "user":
            last_user_message = message["content"]
            last_user_message_id = message["id"]
            break

    if is_cp_format(last_user_message):
        import pyperclip

        cp_id = int(last_user_message.split(" ")[1])
        for message in reversed(messages):
            if message["id"] == cp_id:
                # copy the content of the message to the clipboard
                pyperclip.copy(message["content"])
                insert_chat_message("info", f"Copied msg {cp_id} to clipboard")
    elif "@memorize" in last_user_message:
        assistant_msg = None
        for message in reversed(messages):
            if message["role"] == "assistant":
                assistant_msg = message["content"]
                break
        stand_alone_func = await get_standalone_func(assistant_msg)
        # append the function to the end of the file agent_utils.py
        with open(UTILS_FILE, "a") as f:
            f.write("\n\n" + stand_alone_func)
        insert_chat_message("info", f"Inserted to {UTILS_FILE}:\n" + stand_alone_func)

    elif last_user_message[:8] == "@autogen":
        insert_chat_message("info", "Generating code...")
        await handle_autogen(last_user_message_id)

    elif last_user_message and "@autogen" in last_user_message:
        # get the second last assistant message
        msg_id = None
        for message in reversed(messages):
            if message["role"] == "assistant":
                msg_id = message["id"]
                break
        insert_chat_message("info", f"Generating code using last assistant message {msg_id}...")
        await handle_autogen(msg_id)

    else:
        filtered_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] in ["assistant", "user", "system"]
        ]

        row_id = insert_chat_message("info", "Thinking...")
        logging.info("Checking if the query requires direct response or coding")
        requires_autogen = await check_requires_autogen(filtered_messages, row_id)
        insert_chat_message("info", f"requires_autogen: {requires_autogen}", row_id)

        if requires_autogen is None:
            respond_directly = True
        elif requires_autogen.get("requires_code", None) is False:
            respond_directly = True
        else:
            respond_directly = False

        if respond_directly:
            system_message = {
                "role": "system",
                "content": META_SYSTEM_MESSAGE,
            }

            filtered_messages = [system_message] + filtered_messages
            logging.info(f"Generating direct response for {last_user_message_id}", row_id)
            insert_chat_message("info", "Thinking...", row_id)
            response = await chat_completion_wrapper(
                row_id=row_id, messages=truncate_messages(filtered_messages, MODEL)
            )
            if response is not None:
                insert_chat_message(response["role"], response["content"], row_id=response["id"])
        else:
            logging.info(
                f"Generating code to answer {last_user_message_id} (conf: {requires_autogen['confidence']})..."
            )
            insert_chat_message(
                "info",
                "Thinking more deeply...",
                row_id,
            )
            await handle_autogen(last_user_message_id)


async def check_requires_autogen(messages: List[Dict[str, str]], row_id: int) -> Dict[str, str] or None:
    """
    Given the last message use a gpt call to determine whether
    the query requires autogen.

    Args:
        messages (list): List of messages in the conversation.
        row_id (int): The row ID of the conversation.

    Returns:
        dict or None: A dictionary with the following keys:
            - "requires_code": True or False indicating whether the query requires code.
            - "confidence": A number between 0 and 1 indicating the confidence in the answer.
            Returns None if the response is not a valid JSON object.
    """
    last_messages = messages[-5:]
    query = "\n".join([f"{m['role']}: {m['content']}" for m in last_messages])

    prompt = f"""
    Below is a conversation between a user and an assistant.
    Does correctly satisfactorily responding to the user's last message require
    writing python or shell code? Answer smartly.

    Queries that require code:
    - queries that require websearch
    - queries that require finding something on the web
    - queries that require printing
    - queries that require file handling
    - queries that require creating, modifying, reading files
    - queries that require answering questions about a pdf file or urls

    Queries that dont require code:
    - simple chit chat
    - simple reformatting of provided text

    Respond with a json object with the following keys:
    - "requires_code": true or false
    - "confidence": a number between 0 and 1 indicating your confidence in the answer

    <conversation>
    {query}
    </conversation>

    Only respond with a valid json object.
    """
    response = await chat_completion_wrapper(row_id=row_id, messages=[{"role": "user", "content": prompt}])
    # response = await chat_completion_wrapper()
    response = response["content"]
    # check if the response is valid json
    try:
        response = json.loads(response)
        return response
    except json.decoder.JSONDecodeError:
        if '"requires_code": true' in response:
            return {"requires_code": True, "confidence": 1.0}
        return None


# TODO: Improve documentation for functions below


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
        display_name = USER_NAME
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

    def set_id(self, msg_id):
        self.msg_id = msg_id
        # self.message = fetch_row(self.msg_id)

    def on_mount(self) -> None:
        self.set_interval(0.2, self.update_message)

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

    dirpath = os.path.join(DATA_PATH, "work_dir")
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
        ("ctrl+t", "toggle_dark", "Toggle dark mode"),
        ("ctrl+o", "request_quit", "Quit TinyRA"),
    ]

    CSS_PATH = "tui.css"

    TITLE = "TinyRA"
    SUB_TITLE = "A minimalistic Research Assistant"

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

    def action_request_quit(self) -> None:
        self.push_screen(QuitScreen())

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

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

    @work()
    async def handle_input(self, user_input: str) -> None:
        row_id = insert_chat_message("user", user_input)
        self.generate_response(msg_idx=row_id - 1)

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
                await a_insert_chat_message("info", update_message, msg_idx + 2)
            else:
                num_messages = len(messages)
                await a_insert_chat_message("info", f"Num messages...{num_messages}", msg_idx + 2)
            return False, None

        assistant = AssistantAgent(
            "assistant",
            llm_config=LLM_CONFIG,
        )
        user = UserProxyAgent(
            "user",
            code_execution_config={"work_dir": os.path.join(DATA_PATH, "work_dir")},
            human_input_mode="NEVER",
            is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
        )
        assistant.register_reply(Agent, AssistantAgent.a_generate_oai_reply, 2)
        assistant.register_reply(Agent, post_update_to_main, 1)

        for msg in chat_history:
            if msg["role"] == "user":
                await user.a_send(msg["content"], assistant, request_reply=False, silent=True)
            else:
                await assistant.a_send(msg["content"], user, request_reply=False, silent=True)

        await user.a_initiate_chat(assistant, message=task, clear_history=False)

        last_message = assistant.chat_messages[user][-1]["content"]
        # status_widget.update(f"Completed. Last message from conv: {last_message}")

        await a_insert_chat_message("assistant", last_message, msg_idx + 2)


def run_app() -> None:
    """
    Run the TinyRA app.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset chat history")
    parser.add_argument("--reset-all", action="store_true", help="Reset chat history and delete data path")
    args = parser.parse_args()

    if args.reset_all:
        print(f"Warning: Resetting chat history and deleting data path {DATA_PATH}")
        print("Press enter to continue or Ctrl+C to cancel.")
        input()
        if os.path.exists(CHATDB):
            os.remove(CHATDB)
        if os.path.exists(DATA_PATH):
            shutil.rmtree(DATA_PATH)
        return

    if args.reset:
        print(f"Warning: Resetting chat history. This will delete all chat history in {CHATDB}")
        print("Press enter to continue or Ctrl+C to cancel.")
        input()
        if os.path.exists(CHATDB):
            os.remove(CHATDB)
        return

    app = TinyRA()
    app.run()


if __name__ == "__main__":
    run_app()
