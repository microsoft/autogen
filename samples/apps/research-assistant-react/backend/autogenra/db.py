

import logging
import sqlite3
import threading
import os
from typing import Any

lock = threading.Lock()
logger = logging.getLogger()

class DBManager():

    def __init__(self, path: str = "database.sqlite", **kwargs: Any) -> None: 
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
        # Connect to the database (or create a new one if it doesn't exist)
        self.conn = sqlite3.connect(path, check_same_thread=False, **kwargs)
        self.cursor = self.conn.cursor()

        # Create the table with the specified columns, appropriate data types, and a UNIQUE constraint on (rootMsgId, msgId)
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS messages (
            userId TEXT NOT NULL,
            rootMsgId TEXT NOT NULL,
            msgId TEXT ,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            timestamp DATETIME ,
            UNIQUE (userId,rootMsgId, msgId)
        )
        """
        )

        # Create a table for personalization profiles
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS personalization_profiles (
            userId INTEGER NOT NULL,
            profile TEXT,
            timestamp DATETIME NOT NULL,
            UNIQUE (userId)
        )
        """
        )

        # Commit the changes and close the connection
        self.conn.commit() 
    
    
    
    def query(self, query, args=(), json=False):
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
    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()