import aiosqlite
import logging
from pathlib import Path
from typing import Optional

from ..exceptions import DatabaseError
from .database import ChatHistory, ChatMessage, User


class SQLLiteDatabaseManager:

    DEFAULT_DB_FILE = "tinyra.db"

    def __init__(self, data_path: Path):
        self.database_path = data_path / self.DEFAULT_DB_FILE
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """
        Initialize the database and create the necessary tables.
        """
        try:
            await self.create_user_table()
            await self.create_chat_history_table()
        except Exception as e:
            raise DatabaseError("Error initializing database", e)

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
                "CREATE TABLE IF NOT EXISTS chat_history (root_id INTEGER, id INTEGER, role TEXT, content TEXT)"
            )
            await conn.commit()

    async def get_chat_history(self) -> ChatHistory:
        try:
            self._get_chat_history()
        except aiosqlite.Error as e:
            raise DatabaseError("Error fetching chat history", e)

    async def get_chat_message(self, root_id: int, id: int) -> ChatMessage:
        try:
            self._get_chat_message(root_id, id)
        except aiosqlite.Error as e:
            raise DatabaseError("Error fetching chat message", e)

    async def set_chat_message(self, message: ChatMessage):
        try:
            self._set_chat_message(message)
        except aiosqlite.Error as e:
            raise DatabaseError("Error setting chat message", e)

    async def get_user(self) -> User:
        try:
            self._get_user()
        except aiosqlite.Error as e:
            raise DatabaseError("Error fetching user", e)

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
            await c.execute("SELECT root_id, id, role, content FROM chat_history WHERE root_id = ?", (root_id,))
            chat_history = [
                ChatMessage(root_id=root_id, id=id, role=role, content=content)
                for root_id, id, role, content in await c.fetchall()
            ]
            return ChatHistory(root_id=root_id, messages=chat_history)

    async def _get_chat_message(self, id: int, root_id: int = 0) -> Optional[ChatMessage]:
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
            await c.execute("SELECT role, content FROM chat_history WHERE id = ? AND root_id = ?", (id, root_id))
            row = [
                {"role": role, "content": content, "id": id, "root_id": root_id} for role, content in await c.fetchall()
            ]
            return ChatMessage(**row[0]) if row else None

    async def _set_chat_message(self, message: ChatMessage) -> None:
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

    async def _get_user(self) -> User:
        """
        Query the database for user's information.

        Returns:
            A User object.
        """
        async with aiosqlite.connect(self.database_path) as conn:
            c = await conn.cursor()
            await c.execute("SELECT user_name FROM configuration")
            user_name = (await c.fetchone())[0]
            return User(name=user_name)
