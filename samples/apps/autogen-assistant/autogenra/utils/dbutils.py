import json
import logging
import sqlite3
import threading
import os
from typing import Any, List, Dict, Tuple
from ..datamodel import Gallery, Message, Session


MESSAGES_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS messages (
                user_id TEXT NOT NULL,
                session_id TEXT,
                root_msg_id TEXT NOT NULL,
                msg_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp DATETIME,
                UNIQUE (user_id, root_msg_id, msg_id)
            )
            """

SESSIONS_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                flow_config TEXT,
                UNIQUE (user_id, session_id)
            )
            """

SKILLS_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                flow_config TEXT,
                UNIQUE (user_id, session_id)
            )
            """
GALLERY_TABLE_SQL = """
            CREATE TABLE IF NOT EXISTS gallery (
                gallery_id TEXT NOT NULL,
                session TEXT,
                messages TEXT,
                tags TEXT,
                timestamp DATETIME NOT NULL,
                UNIQUE ( gallery_id)
            )
            """


lock = threading.Lock()
logger = logging.getLogger()


class DBManager:
    """
    A database manager class that handles the creation and interaction with an SQLite database.
    """

    def __init__(self, path: str = "database.sqlite", **kwargs: Any) -> None:
        """
        Initializes the DBManager object, creates a database if it does not exist, and establishes a connection.

        Args:
            path (str): The file path to the SQLite database file.
            **kwargs: Additional keyword arguments to pass to the sqlite3.connect method.
        """
        self.path = path
        # check if the database exists, if not create it
        if not os.path.exists(self.path):
            logger.info("Creating database")
            self.init_db(path=self.path, **kwargs)

        try:
            self.conn = sqlite3.connect(self.path, check_same_thread=False, **kwargs)
            self.cursor = self.conn.cursor()
        except Exception as e:
            logger.error("Error connecting to database: %s", e)
            raise e

    def init_db(self, path: str = "database.sqlite", **kwargs: Any) -> None:
        """
        Initializes the database by creating necessary tables.

        Args:
            path (str): The file path to the SQLite database file.
            **kwargs: Additional keyword arguments to pass to the sqlite3.connect method.
        """
        # Connect to the database (or create a new one if it doesn't exist)
        self.conn = sqlite3.connect(path, check_same_thread=False, **kwargs)
        self.cursor = self.conn.cursor()

        # Create the table with the specified columns, appropriate data types, and a UNIQUE constraint on (root_msg_id, msg_id)
        self.cursor.execute(MESSAGES_TABLE_SQL)

        # Create a sessions table
        self.cursor.execute(SESSIONS_TABLE_SQL)

        # Create a  skills
        self.cursor.execute(SKILLS_TABLE_SQL)

        # Create a gallery table
        self.cursor.execute(GALLERY_TABLE_SQL)

        # Commit the changes and close the connection
        self.conn.commit()

    def query(self, query: str, args: Tuple = (), return_json: bool = False) -> List[Dict[str, Any]]:
        """
        Executes a given SQL query and returns the results.

        Args:
            query (str): The SQL query to execute.
            args (Tuple): The arguments to pass to the SQL query.
            return_json (bool): If True, the results will be returned as a list of dictionaries.

        Returns:
            List[Dict[str, Any]]: The result of the SQL query.
        """
        try:
            with lock:
                self.cursor.execute(query, args)
                result = self.cursor.fetchall()
                self.commit()
                if return_json:
                    result = [dict(zip([key[0] for key in self.cursor.description], row)) for row in result]
                return result
        except Exception as e:
            logger.error("Error running query with query %s and args %s: %s", query, args, e)
            raise e

    def commit(self) -> None:
        """
        Commits the current transaction to the database.
        """
        self.conn.commit()

    def close(self) -> None:
        """
        Closes the database connection.
        """
        self.conn.close()


def save_message(message: Message, dbmanager: DBManager) -> None:
    """
    Save a message in the database using the provided database manager.

    :param message: The Message object containing message data
    :param dbmanager: The DBManager instance used to interact with the database
    """
    query = "INSERT INTO messages (user_id, root_msg_id, msg_id, role, content, metadata, timestamp, session_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    args = (
        message.user_id,
        message.root_msg_id,
        message.msg_id,
        message.role,
        message.content,
        message.metadata,
        message.timestamp,
        message.session_id,
    )
    dbmanager.query(query=query, args=args)


def load_messages(user_id: str, session_id: str, dbmanager: DBManager) -> List[dict]:
    """
    Load messages for a specific user and session from the database, sorted by timestamp.

    :param user_id: The ID of the user whose messages are to be loaded
    :param session_id: The ID of the session whose messages are to be loaded
    :param dbmanager: The DBManager instance to interact with the database

    :return: A list of dictionaries, each representing a message
    """
    query = "SELECT * FROM messages WHERE user_id = ? AND session_id = ?"
    args = (user_id, session_id)
    result = dbmanager.query(query=query, args=args, return_json=True)
    # Sort by timestamp ascending
    result = sorted(result, key=lambda k: k["timestamp"], reverse=False)
    return result


def get_sessions(user_id: str, dbmanager: DBManager) -> List[dict]:
    """
    Load sessions for a specific user from the database, sorted by timestamp.

    :param user_id: The ID of the user whose sessions are to be loaded
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing a session
    """
    query = "SELECT * FROM sessions WHERE user_id = ?"
    args = (user_id,)
    result = dbmanager.query(query=query, args=args, return_json=True)
    # Sort by timestamp ascending
    result = sorted(result, key=lambda k: k["timestamp"], reverse=True)
    for row in result:
        row["flow_config"] = json.loads(row["flow_config"])
    return result


def create_session(user_id: str, session: Session, dbmanager: DBManager) -> List[dict]:
    """
    Create a new session for a specific user in the database.

    :param user_id: The ID of the user whose session is to be created
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing a session
    """

    query = "INSERT INTO sessions (user_id, session_id, timestamp, flow_config) VALUES (?, ?, ?,?)"
    args = (session.user_id, session.session_id, session.timestamp, json.dumps(session.flow_config.dict()))
    dbmanager.query(query=query, args=args)
    sessions = get_sessions(user_id=user_id, dbmanager=dbmanager)

    return sessions


def publish_session(session: Session, dbmanager: DBManager, tags: List[str] = []) -> Gallery:
    """
    Publish a session to the gallery table in the database. Fetches the session messages first, then saves session and messages object to the gallery database table.
    :param session: The Session object containing session data
    :param dbmanager: The DBManager instance used to interact with the database
    :param tags: A list of tags to associate with the session
    :return: A gallery object containing the session and messages objects
    """

    messages = load_messages(user_id=session.user_id, session_id=session.session_id, dbmanager=dbmanager)
    gallery_item = Gallery(session=session, messages=messages, tags=tags)
    query = "INSERT INTO gallery (gallery_id, session, messages, tags, timestamp) VALUES (?, ?, ?, ?,?)"
    args = (
        gallery_item.id,
        json.dumps(gallery_item.session.dict()),
        json.dumps([message.dict() for message in gallery_item.messages]),
        json.dumps(gallery_item.tags),
        gallery_item.timestamp,
    )
    dbmanager.query(query=query, args=args)
    return gallery_item


def get_gallery(gallery_id, dbmanager: DBManager) -> List[Gallery]:
    """
    Load gallery items from the database, sorted by timestamp. If gallery_id is provided, only the gallery item with the matching gallery_id will be returned.

    :param gallery_id: The ID of the gallery item to be loaded
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of Gallery objects
    """

    if gallery_id:
        query = "SELECT * FROM gallery WHERE gallery_id = ?"
        args = (gallery_id,)
    else:
        query = "SELECT * FROM gallery"
        args = ()
    result = dbmanager.query(query=query, args=args, return_json=True)
    # Sort by timestamp ascending
    result = sorted(result, key=lambda k: k["timestamp"], reverse=True)
    gallery = []
    for row in result:
        gallery_item = Gallery(
            id=row["gallery_id"],
            session=Session(**json.loads(row["session"])),
            messages=[Message(**message) for message in json.loads(row["messages"])],
            tags=json.loads(row["tags"]),
            timestamp=row["timestamp"],
        )
        gallery.append(gallery_item)
    return gallery


def delete_user_sessions(user_id: str, session_id: str, dbmanager: DBManager, delete_all: bool = False) -> List[dict]:
    """
    Delete a specific session or all sessions for a user from the database.

    :param user_id: The ID of the user whose session is to be deleted
    :param session_id: The ID of the specific session to be deleted (ignored if delete_all is True)
    :param dbmanager: The DBManager instance to interact with the database
    :param delete_all: If True, all sessions for the user will be deleted
    :return: A list of the remaining sessions if not all were deleted, otherwise an empty list
    """
    if delete_all:
        query = "DELETE FROM sessions WHERE user_id = ?"
        args = (user_id,)
        dbmanager.query(query=query, args=args)
        return []
    else:
        query = "DELETE FROM sessions WHERE user_id = ? AND session_id = ?"
        args = (user_id, session_id)
        dbmanager.query(query=query, args=args)
        sessions = get_sessions(user_id=user_id, dbmanager=dbmanager)

        return sessions


def delete_message(
    user_id: str, msg_id: str, session_id: str, dbmanager: DBManager, delete_all: bool = False
) -> List[dict]:
    """
    Delete a specific message or all messages for a user and session from the database.

    :param user_id: The ID of the user whose messages are to be deleted
    :param msg_id: The ID of the specific message to be deleted (ignored if delete_all is True)
    :param session_id: The ID of the session whose messages are to be deleted
    :param dbmanager: The DBManager instance to interact with the database
    :param delete_all: If True, all messages for the user will be deleted
    :return: A list of the remaining messages if not all were deleted, otherwise an empty list
    """

    if delete_all:
        query = "DELETE FROM messages WHERE user_id = ? AND session_id = ?"
        args = (user_id, session_id)
        dbmanager.query(query=query, args=args)
        return []
    else:
        query = "DELETE FROM messages WHERE user_id = ? AND msg_id = ? AND session_id = ?"
        args = (user_id, msg_id, session_id)
        dbmanager.query(query=query, args=args)
        messages = load_messages(user_id=user_id, session_id=session_id, dbmanager=dbmanager)
        return messages
