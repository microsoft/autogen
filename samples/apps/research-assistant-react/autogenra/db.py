import logging
import sqlite3
import threading
import os
from typing import Any, List, Dict, Tuple

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
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                user_id TEXT NOT NULL,
                root_msg_id TEXT NOT NULL,
                msg_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp DATETIME,
                UNIQUE (user_id, root_msg_id, msg_id)
            )
            """
        )

        # Create a table for personalization profiles
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS personalization_profiles (
                user_id INTEGER NOT NULL,
                profile TEXT,
                timestamp DATETIME NOT NULL,
                UNIQUE (user_id)
            )
            """
        )

        # Commit the changes and close the connection
        self.conn.commit()

    def query(self, query: str, args: Tuple = (), json: bool = False) -> List[Dict[str, Any]]:
        """
        Executes a given SQL query and returns the results.

        Args:
            query (str): The SQL query to execute.
            args (Tuple): The arguments to pass to the SQL query.
            json (bool): If True, the results will be returned as a list of dictionaries.

        Returns:
            List[Dict[str, Any]]: The result of the SQL query.
        """
        try:
            with lock:
                self.cursor.execute(query, args)
                result = self.cursor.fetchall()
                self.commit()
                if json:
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
