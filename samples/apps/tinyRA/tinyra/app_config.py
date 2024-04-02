import os
import platform
import sqlite3
import shutil
import logging

from typing import Dict, Optional

from autogen import AssistantAgent

from .tools import Tool
from .exceptions import ToolUpdateError


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
        # work dir must reside in the data path
        self._work_dir = os.path.join(data_path, "work_dir")

    def initialize(self):
        """Initialize the app configuration."""
        # create the data path if it does not exist
        os.makedirs(self._data_path, exist_ok=True)
        os.makedirs(self._work_dir, exist_ok=True)

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

    def update_configuration(
        self, user_name: Optional[str] = None, user_bio: Optional[str] = None, user_preferences: Optional[str] = None
    ):
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

    def get_workdir(self):
        return self._work_dir

    def update_tool(self, tool: Tool):
        try:
            conn = sqlite3.connect(self._database_path)
            c = conn.cursor()
            c.execute("SELECT * FROM tools WHERE id = ?", (tool.id,))
            if c.fetchone() is None:
                c.execute(
                    "INSERT INTO tools (name, code, description) VALUES (?, ?, ?)",
                    (tool.name, tool.code, tool.description),
                )
            else:
                c.execute(
                    "UPDATE tools SET name = ?, code = ?, description = ? WHERE id = ?",
                    (tool.name, tool.code, tool.description, tool.id),
                )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            raise ToolUpdateError(f"Error updating tool! {e}")

    def get_tools(self, tool_id=None) -> Dict[int, Tool]:
        conn = sqlite3.connect(self._database_path)
        c = conn.cursor()

        tools = {}
        if tool_id is not None:
            c.execute("SELECT id, name, code, description FROM tools WHERE id=?", (tool_id,))
            tool = c.fetchone()
            if tool is not None:
                id, name, code, description = tool
                tools[id] = Tool(name, code, description, id=id)
        else:
            c.execute("SELECT id, name, code, description FROM tools")
            for id, name, code, description in c.fetchall():
                tools[id] = Tool(name, code, description, id=id)

        conn.close()
        return tools

    def delete_tool(self, tool_id: int):
        try:
            conn = sqlite3.connect(self._database_path)
            c = conn.cursor()
            c.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            raise ToolUpdateError(f"Error deleting tool! {e}")

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
