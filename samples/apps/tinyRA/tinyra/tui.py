import os
import asyncio
import ast
import configparser
import platform
import json
import logging

from typing import List, Dict

from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Footer, Header, Markdown, Static, Input
from textual.reactive import reactive

import sqlite3
import tiktoken

from autogen import config_list_from_json
from autogen import AssistantAgent, UserProxyAgent


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


def init_database():
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


MODEL = "gpt-4"
CONFIG = configparser.ConfigParser()
CHATDB = os.path.join(DATA_PATH, "chat_history.db")
if not os.path.exists(CHATDB):
    init_database()
USER_NAME = "Gagan"
USER_PROFILE_TEXT = ""
OPERATING_SYSTEM = platform.system()
UTILS_FILE = os.path.join(DATA_PATH, "agent_utils.py")
if not os.path.exists(UTILS_FILE):
    with open(UTILS_FILE, "w") as f:
        f.write("")
CONFIG_LIST = config_list_from_json("OAI_CONFIG_LIST")
llm_config = config_list_from_json("OAI_CONFIG_LIST")[0]
llm_config["seed"] = 42

# MODEL = ""


def fetch_chat_history() -> List[Dict[str, str]]:
    conn = sqlite3.connect(CHATDB)
    c = conn.cursor()
    c.execute("SELECT id, role, content FROM chat_history")
    chat_history = [{"id": id, "role": role, "content": content} for id, role, content in c.fetchall()]
    conn.close()
    return chat_history


def fetch_row(id) -> Dict[str, str]:
    conn = sqlite3.connect(CHATDB)
    c = conn.cursor()
    c.execute("SELECT role, content FROM chat_history WHERE id = ?", (id,))
    row = [{"role": role, "content": content, "id": id} for role, content in c.fetchall()]
    conn.close()
    return row[0]


def insert_chat_message(role, content, row_id=None):
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
                data = (role, content, row_id)
                c.execute("UPDATE chat_history SET role = ?, content = ? WHERE id = ?", data)
                conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting or updating chat message: {e}")


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
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
        raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.""")


def truncate_messages(messages, model):
    max_context_tokens = None
    if model == "gpt-4-32k":
        max_context_tokens = 32000
    elif model == "gpt-4":
        max_context_tokens = 8000
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
        if prompt_tokens <= max_context_tokens - 1000:
            break
        else:
            start_idx += 1
    return new_messages


async def ask_gpt(messages):
    # filer only role and content keys from the chat history
    messages = [{k: v for k, v in m.items() if k in ["role", "content"]} for m in messages]
    messages = [m for m in messages if m["role"] in ["assistant", "user"]]

    assistant = AssistantAgent("assistant", llm_config=llm_config)
    user = UserProxyAgent("user", code_execution_config=False)

    logging.info(messages)
    for i, message in enumerate(messages):
        if message["role"] == "assistant":
            await assistant.a_send(message, user, request_reply=False)
        elif message["role"] == "user":
            is_last_user_msg = False
            if i == len(messages) - 1:
                is_last_user_msg = True
            await user.a_send(message, assistant, request_reply=is_last_user_msg)

    logging.info(assistant.chat_messages)
    response = assistant.chat_messages[user][-1]
    logging.info(response)
    return response


async def chat_completion_wrapper(row_id, *args, **kwargs):
    max_retries = 500
    count = 0
    # row_id = insert_chat_message("info", "Requesting response...")
    while True:
        try:
            response = await ask_gpt(kwargs["messages"])
            response["id"] = row_id
            return response
        except Exception as e:
            count += 1
            if count > max_retries:
                insert_chat_message("error", f"{e}", row_id)
                return None
            insert_chat_message("info", f"Retrying again ({count})...{e}", row_id)
            await asyncio.sleep(2)  # You can adjust the retry delay as needed.


def function_names_to_markdown_table(file_path):
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


def get_available_functions():
    markdown_table = function_names_to_markdown_table(UTILS_FILE)
    return markdown_table


def json_to_markdown_code_block(json_data, pretty_print=True):
    if pretty_print:
        json_string = json.dumps(json_data, indent=2)
    else:
        json_string = json.dumps(json_data)

    markdown_code_block = f"```json\n{json_string}\n```"
    return markdown_code_block


async def handle_autogen(msg_id):
    import subprocess

    script_path = os.path.join(os.path.dirname(__file__), "run_tinyra.sh")
    subprocess.run(["bash", script_path, "tab", str(msg_id)], check=True)


async def get_standalone_func(content):
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
    response = await chat_completion_wrapper(
        row_id=row_id,
        model=MODEL,
        messages=messages,
        max_tokens=800,
    )

    return response["content"]


def is_cp_format(string):
    import re

    pattern = r"cp \d+$"
    return bool(re.match(pattern, string))


async def handle_user_input():
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

        row_id = insert_chat_message("info", "Checking if the query requires decomposition...")
        requires_autogen = await check_requires_autogen(filtered_messages, row_id)
        insert_chat_message("info", f"requires_autogen: {requires_autogen}", row_id)

        if requires_autogen is None:
            respond_directly = True
        elif requires_autogen.get("requires_code", None) is False:
            respond_directly = True
        else:
            respond_directly = False

        requires_autogen = {"requires_code": True, "confidence": 1.0}
        respond_directly = False

        # respond_directly = requires_autogen is not None and requires_autogen["requires_code"] == False

        if respond_directly:
            system_message = {
                "role": "system",
                "content": f"""
                            You are a helpful researcher assistant named "tinyRA".
                            You are running on {OPERATING_SYSTEM} operating system.
                            You are here to help {USER_NAME} with his research.
                            The following is the bio of {USER_NAME}:

                            <bio>
                            {USER_PROFILE_TEXT}
                            </bio>

                            Respond to {USER_NAME}'s messages to be most helpful.
                            """,
            }

            filtered_messages = [system_message] + filtered_messages
            insert_chat_message("info", f"Generating direct response for {last_user_message_id}", row_id)
            response = await chat_completion_wrapper(
                row_id=row_id,
                model=MODEL,
                messages=truncate_messages(filtered_messages, MODEL),
                max_tokens=800,
            )
            if response is not None:
                insert_chat_message(response["role"], response["content"], row_id=response["id"])
        else:
            insert_chat_message(
                "info",
                f"Generating code to answer {last_user_message_id} (conf: {requires_autogen['confidence']})...",
                row_id,
            )
            await handle_autogen(last_user_message_id)


async def check_requires_autogen(messages, row_id):
    """
    Given the last message use a gpt call to determine whether
    the query requires autogen.
    """
    last_messages = messages[-5:]
    query = "\n".join([f"{m['role']}: {m['content']}" for m in last_messages])

    prompt = f"""
    Below is a conversation between a user and an assistant.
    Does correctly satisfactorly responding to the user's last message require
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
    response = await chat_completion_wrapper(
        row_id=row_id,
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
    )
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


def message2markdown(message):
    role = message["role"]
    content = message["content"]
    id = message["id"]
    return f"[{id}] {role.capitalize()}: {content}"


class ReactiveAssistantMessage(Markdown):
    message = reactive({"role": "assistant", "content": "loading...", "id": -1})

    def set_id(self, msg_id):
        self.msg_id = msg_id
        # self.message = fetch_row(self.msg_id)

    def on_mount(self) -> None:
        self.set_interval(1, self.update_message)

    def update_message(self):
        self.message = fetch_row(self.msg_id)
        self.classes = f"{self.message['role'].lower()}-message message"

    def watch_message(self) -> str:
        role = self.message["role"]
        if role not in ["info", "error"]:
            self.scroll_visible()
        self.update(message2markdown(self.message))


def message_display_handler(message):
    role = message["role"]
    if role == "user":
        text = Markdown(message2markdown(message), classes=f"{role.lower()}-message message")
    else:
        id = message["id"]
        text = ReactiveAssistantMessage(classes=f"{role.lower()}-message message")
        text.set_id(id)
    return text


class SkillsDisplayContainer(ScrollableContainer):
    def compose(self) -> ComposeResult:
        yield SkillsDisplay()


class SkillsDisplay(Markdown):
    skills = reactive(get_available_functions)

    def watch_skills(self) -> None:
        self.update(self.skills)

    def on_mount(self) -> None:
        self.set_interval(5, self.update_skills)

    def update_skills(self):
        self.skills = get_available_functions()

    # def compose(self) -> ComposeResult:
    #     yield Markdown(self.skills)


class ChatDisplay(ScrollableContainer):
    limit_history = 100
    chat_history = reactive(fetch_chat_history)
    old_chat_history = reactive(fetch_chat_history)

    def on_mount(self) -> None:
        self.set_interval(1.0, self.update_chat_history)

    def update_chat_history(self) -> None:
        self.chat_history = fetch_chat_history()

    def watch_chat_history(self) -> None:
        len_old = len(self.old_chat_history)
        len_new = len(self.chat_history)
        # add widgets for new messages
        for i in range(len_old, len_new):
            text = message_display_handler(self.chat_history[i])
            self.mount(text)
            if i == len_new - 1:
                text.scroll_visible()
        self.old_chat_history = self.chat_history

    def compose(self) -> ComposeResult:
        for message in self.chat_history[-self.limit_history :]:
            widget = message_display_handler(message)
            yield widget


class ChatInput(Static):
    def on_mount(self) -> None:
        input = self.query_one(Input)
        input.focus()

    def compose(self) -> ComposeResult:
        yield Input()


class TinyRA(App):
    """A Textual app to display chat history."""

    BINDINGS = [
        ("ctrl+t", "toggle_dark", "Toggle dark mode"),
        ("ctrl+c", "request_quit", "Quit TinyRA"),
        ("ctrl+r", "handle_again", "Retry Last User Msg"),
        ("ctrl+g", "memorize_autogen", "Memorize"),
    ]

    CSS_PATH = "tui.css"

    TITLE = "TinyRA"
    SUB_TITLE = "A minimalistic Research Assistant"

    def on_mount(self) -> None:
        self.query_one(ChatDisplay).scroll_end(animate=False)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield ChatDisplay(id="chat-history")
        yield SkillsDisplayContainer(id="skills")
        yield ChatInput(id="chat-input")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        content = self.query_one(Input).value.strip()
        insert_chat_message("user", content)
        self.query_one(Input).value = ""
        self.run_worker(handle_user_input())

    def action_request_quit(self) -> None:
        self.app.exit()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_evoke_autogen(self) -> None:
        insert_chat_message("user", "Evoke @autogen")
        self.run_worker(handle_user_input())

    def action_handle_again(self) -> None:
        self.run_worker(handle_user_input())

    def action_memorize_autogen(self) -> None:
        insert_chat_message("user", "lets @memorize")
        self.run_worker(handle_user_input())


def main() -> None:
    app = TinyRA()
    app.run()


def run_tinyra():
    import subprocess

    script_path = os.path.join(os.path.dirname(__file__), "run_tinyra.sh")
    subprocess.run(["bash", script_path], check=True)


if __name__ == "__main__":
    main()
