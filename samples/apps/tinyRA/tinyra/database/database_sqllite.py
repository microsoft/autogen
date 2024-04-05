import os
import aiosqlite
import logging
from pathlib import Path
from typing import Optional

from ..exceptions import DatabaseError
from .database import ChatHistory, ChatMessage, User


class SQLLiteDatabaseManager:

    DEFAULT_DB_FILE = "tinyra.db"
    DEFAULT_USER = User(name="Default User", bio="", preferences="")

    def __init__(self, data_path: Path):
        self.database_path = data_path / self.DEFAULT_DB_FILE
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """
        Initialize the database and create the necessary tables.
        """
        self.logger.info(f"Initializing database at {self.database_path}")
        try:
            self.logger.info("Creating user table")
            await self.create_user_table()
            self.logger.info("Creating chat history table")
            await self.create_chat_history_table()
        except Exception as e:
            raise DatabaseError("Error initializing database", e)

    async def _create_default_user(self):
        current_user = await self.get_user()
        if not current_user:
            default_user = self.DEFAULT_USER
            # try getting the name from the environment
            default_user.name = os.getenv("USER_NAME", default_user.name)
            await self.set_user(default_user)

    async def create_user_table(self):
        """
        Create the user table in the database.
        """
        self.logger.info(f"Creating table config in {self.database_path}")
        async with aiosqlite.connect(self.database_path) as conn:
            c = await conn.cursor()
            await c.execute("CREATE TABLE IF NOT EXISTS configuration (user_name TEXT, bio TEXT, preferences TEXT)")
            await conn.commit()

    async def create_chat_history_table(self):
        """
        Create the chat history table in the database.
        """
        self.logger.info(f"Creating table config in {self.database_path}")
        async with aiosqlite.connect(self.database_path) as conn:
            c = await conn.cursor()
            await c.execute(
                "CREATE TABLE IF NOT EXISTS chat_history (root_id INTEGER, id INTEGER, role TEXT, content TEXT, timestamp FLOAT)"
            )
            await conn.commit()

    async def get_chat_history(self, root_id: int) -> ChatHistory:
        try:
            return await self._get_chat_history(root_id=root_id)
        except aiosqlite.Error as e:
            raise DatabaseError("Error fetching chat history", e)

    async def get_chat_message(self, root_id: int, id: int) -> ChatMessage:
        try:
            return await self._get_chat_message(root_id, id)
        except aiosqlite.Error as e:
            raise DatabaseError("Error fetching chat message", e)

    async def set_chat_message(self, message: ChatMessage) -> ChatMessage:
        try:
            return await self._set_chat_message(message)
        except aiosqlite.Error as e:
            raise DatabaseError("Error setting chat message", e)

    async def get_user(self) -> User:
        try:
            return await self._get_user()
        except aiosqlite.Error as e:
            raise DatabaseError("Error fetching user", e)

    async def set_user(self, user: User) -> User:
        try:
            return await self._set_user(user)
        except aiosqlite.Error as e:
            raise DatabaseError("Error setting user", e)

    async def _set_user(self, user: User) -> User:
        """
        Set the user's information in the database.

        Args:
            user: the User object to set

        Returns:
            A User object.
        """
        async with aiosqlite.connect(self.database_path) as conn:
            c = await conn.cursor()
            await c.execute("SELECT user_name FROM configuration")
            if (await c.fetchone()) is None:
                data = (user.name, user.bio, user.preferences)
                await c.execute("INSERT INTO configuration (user_name, bio, preferences) VALUES (?, ?, ?)", data)
                await conn.commit()
            else:
                data = (user.name, user.bio, user.preferences)
                await c.execute("UPDATE configuration SET user_name = ?, bio = ?, preferences = ?", data)
                await conn.commit()
            return user

    async def _get_chat_history(self, root_id: int = 0) -> ChatHistory:
        """
        Fetch the chat history from the database.

        Args:
            root_id: the root id of the messages to fetch. If None, all messages are fetched.

        Returns:
            A ChatHistory object.
        """
        async with aiosqlite.connect(self.database_path) as conn:
            c = await conn.cursor()
            await c.execute(
                "SELECT root_id, id, role, content, timestamp FROM chat_history WHERE root_id = ?", (root_id,)
            )
            chat_history = [
                ChatMessage(root_id=root_id, id=id, role=role, content=content, timestamp=timestamp)
                for root_id, id, role, content, timestamp in await c.fetchall()
            ]
            return ChatHistory(root_id=root_id, messages=chat_history)

    async def _get_chat_message(self, root_id: int, id: int) -> Optional[ChatMessage]:
        """
        Fetch a single chat message from the database.

        Args:
            id: the id of the message to fetch
            root_id: the root id of the message to fetch. If not specified, it's assumed to be 0.

        Returns:
            A single ChatMessage object.
        """
        async with aiosqlite.connect(self.database_path) as conn:
            c = await conn.cursor()
            await c.execute(
                "SELECT role, content, timestamp FROM chat_history WHERE id = ? AND root_id = ?", (id, root_id)
            )
            row = [
                {"role": role, "content": content, "id": id, "root_id": root_id, "timestamp": timestamp}
                for role, content, timestamp in await c.fetchall()
            ]
            return ChatMessage(**row[0]) if row else None

    async def _set_chat_message(self, message: ChatMessage) -> ChatMessage:
        """
        Insert or update a chat message in the database.

        Args:
            message: the ChatMessage object to insert or update

        Raises:
            ChatMessageError: if there's an error inserting or updating the chat message
        """
        async with aiosqlite.connect(self.database_path) as conn:
            c = await conn.cursor()
            if message.id is None:
                await c.execute("SELECT MAX(id) FROM chat_history WHERE root_id = ?", (message.root_id,))
                item = await c.fetchone()
                max_id = None
                if item is not None:
                    max_id = item[0]
                message.id = max_id + 1 if max_id is not None else 0
                data_a = (message.root_id, message.id, message.role, message.content)
                await c.execute("INSERT INTO chat_history (root_id, id, role, content) VALUES (?, ?, ?, ?)", data_a)
                await conn.commit()
                return message
            else:
                await c.execute(
                    "SELECT * FROM chat_history WHERE root_id = ? AND id = ?", (message.root_id, message.id)
                )
                if await c.fetchone() is None:
                    data_b = (message.root_id, message.id, message.role, message.content)
                    await c.execute("INSERT INTO chat_history (root_id, id, role, content) VALUES (?, ?, ?, ?)", data_b)
                    await conn.commit()
                else:
                    data_c = (message.role, message.content, message.root_id, message.id)
                    await c.execute(
                        "UPDATE chat_history SET role = ?, content = ? WHERE root_id = ? AND id = ?", data_c
                    )
                    await conn.commit()
                return message

    async def _get_user(self) -> User:
        """
        Query the database for user's information.

        Returns:
            A User object.
        """
        async with aiosqlite.connect(self.database_path) as conn:
            c = await conn.cursor()
            await c.execute("SELECT user_name FROM configuration")
            output = await c.fetchone()

            if output is None:
                return self.get_default_user()

            user_name, bio, preferences = output
            return User(name=user_name, bio=bio, preferences=preferences)

    def get_default_user(self) -> User:
        """
        Get the default user.
        """
        default_user = self.DEFAULT_USER
        default_user.name = os.environ.get("USER", self.DEFAULT_USER.name)
        return default_user

    async def reset(self) -> bool:
        """
        Reset the database.
        """
        try:
            await self._reset()
            return True
        except aiosqlite.Error as e:
            raise DatabaseError("Error resetting database", e)

    async def _reset(self):
        """
        Reset the database.
        """
        async with aiosqlite.connect(self.database_path) as conn:
            c = await conn.cursor()
            await c.execute("DROP TABLE IF EXISTS configuration")
            await c.execute("DROP TABLE IF EXISTS chat_history")
            await conn.commit()
