from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import uuid

from autogen.logger.base_logger import BaseLogger
from autogen.logger.logger_utils import get_current_ts, to_dict

from openai import OpenAI, AzureOpenAI
from openai.types.chat import ChatCompletion
from typing import Dict, TYPE_CHECKING, Union


if TYPE_CHECKING:
    from autogen import ConversableAgent, OpenAIWrapper


# this is a pointer to the module object instance itself
this = sys.modules[__name__]
this._session_id = None
logger = logging.getLogger(__name__)

__all__ = ("SqliteLogger",)


class SqliteLogger(BaseLogger):
    schema_version = 1

    def __init__(self, config):
        self.con = None
        self.cur = None
        self.config = config

    def start(self) -> str:
        dbname = self.config["dbname"] if "dbname" in self.config else "logs.db"
        this._session_id = str(uuid.uuid4())

        try:
            self.con = sqlite3.connect(dbname)
            self.cur = self.con.cursor()

            query = """
                CREATE TABLE IF NOT EXISTS chat_completions(
                    id INTEGER PRIMARY KEY,
                    invocation_id TEXT,
                    client_id INTEGER,
                    wrapper_id INTEGER,
                    session_id TEXT,
                    request TEXT,
                    response TEXT,
                    is_cached INEGER,
                    cost REAL,
                    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    end_time DATETIME DEFAULT CURRENT_TIMESTAMP)
            """
            self.cur.execute(query)
            self.con.commit()

            query = """
                CREATE TABLE IF NOT EXISTS agents (
                    id INTEGER PRIMARY KEY,                             -- Key assigned by the database
                    agent_id INTEGER,                                   -- result of python id(agent)
                    wrapper_id INTEGER,                                 -- result of python id(agent.client)
                    session_id TEXT,
                    name TEXT,                                          -- agent.name
                    class TEXT,                                         -- type or class name of agent
                    init_args TEXT,                                     -- JSON serialization of constructor
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(agent_id, session_id))
            """
            self.cur.execute(query)
            self.con.commit()

            query = """
                CREATE TABLE IF NOT EXISTS oai_wrappers (
                    id INTEGER PRIMARY KEY,                             -- Key assigned by the database
                    wrapper_id INTEGER,                                 -- result of python id(wrapper)
                    session_id TEXT,
                    init_args TEXT,                                     -- JSON serialization of constructor
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(wrapper_id, session_id))
            """
            self.cur.execute(query)
            self.con.commit()

            query = """
                CREATE TABLE IF NOT EXISTS oai_clients (
                    id INTEGER PRIMARY KEY,                             -- Key assigned by the database
                    client_id INTEGER,                                  -- result of python id(client)
                    wrapper_id INTEGER,                                 -- result of python id(wrapper)
                    session_id TEXT,
                    class TEXT,                                         -- type or class name of client
                    init_args TEXT,                                     -- JSON serialization of constructor
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(client_id, session_id))
            """
            self.cur.execute(query)
            self.con.commit()

            query = """
            CREATE TABLE IF NOT EXISTS version (
                id INTEGER PRIMARY KEY CHECK (id = 1),                  -- id of the logging database
                version_number INTEGER NOT NULL                         -- version of the logging database
            );
            """
            self.cur.execute(query)
            self.con.commit()

            current_verion = self._get_current_db_version()
            if current_verion is None:
                self.cur.execute(
                    "INSERT INTO version (id, version_number) VALUES (1, ?);", (SqliteLogger.schema_version,)
                )
                self.con.commit()

            self._apply_migration(dbname)

        except sqlite3.Error as e:
            logger.error(f"[SqliteLogger] start logging error: {e}")
        finally:
            return this._session_id

    def _get_current_db_version(self):
        self.cur.execute("SELECT version_number FROM version ORDER BY id DESC LIMIT 1")
        result = self.cur.fetchone()
        return result[0] if result else None

    # Example migration script name format: 002_update_agents_table.sql
    def _apply_migration(self, dbname, migrations_dir="./migrations"):
        current_version = self._get_current_db_version()
        if os.path.isdir(migrations_dir):
            migrations = sorted(os.listdir(migrations_dir))
        else:
            logger.info("no migration scripts, skip...")
            return

        migrations_to_apply = [m for m in migrations if int(m.split("_")[0]) > current_version]

        for script in migrations_to_apply:
            with open(script, "r") as f:
                migration_sql = f.read()
                self.con.executescript(migration_sql)
                self.con.commit()

                latest_version = int(script.split("_")[0])
                self.cur.execute("UPDATE version SET version_number = ? WHERE id = 1", (latest_version))
                self.con.commit()

    def log_chat_completion(
        self,
        invocation_id: uuid.UUID,
        client_id: int,
        wrapper_id: int,
        request: Dict,
        response: Union[str, ChatCompletion],
        is_cached: int,
        cost: float,
        start_time: str,
    ) -> None:
        if self.con is None:
            return

        end_time = get_current_ts()

        if response is None or isinstance(response, str):
            response_messages = json.dumps({"response": response})
        else:
            response_messages = json.dumps(to_dict(response), indent=4)

        query = """
            INSERT INTO chat_completions (
                invocation_id, client_id, wrapper_id, session_id, request, response, is_cached, cost, start_time, end_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            self.cur.execute(
                query,
                (
                    invocation_id,
                    client_id,
                    wrapper_id,
                    this._session_id,
                    json.dumps(request),
                    response_messages,
                    is_cached,
                    cost,
                    start_time,
                    end_time,
                ),
            )
            self.con.commit()
        except sqlite3.Error as e:
            logger.error(f"[SqliteLogger] log_chat_completion error: {e}")

    def log_new_agent(self, agent: ConversableAgent, init_args: Dict) -> None:
        from autogen import Agent

        if self.con is None:
            return

        args = to_dict(
            init_args,
            exclude=("self", "__class__", "api_key", "organization", "base_url", "azure_endpoint"),
            no_recursive=(Agent),
        )

        # We do an upsert since both the superclass and subclass may call this method (in that order)
        query = """
        INSERT INTO agents (agent_id, wrapper_id, session_id, name, class, init_args, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (agent_id, session_id) DO UPDATE SET
            wrapper_id = excluded.wrapper_id,
            name = excluded.name,
            class = excluded.class,
            init_args = excluded.init_args,
            timestamp = excluded.timestamp
        """
        try:
            self.cur.execute(
                query,
                (
                    id(agent),
                    agent.client.wrapper_id if hasattr(agent, "client") and agent.client is not None else "",
                    this._session_id,
                    agent.name if hasattr(agent, "name") and agent.name is not None else "",
                    type(agent).__name__,
                    json.dumps(args),
                    get_current_ts(),
                ),
            )
            self.con.commit()
        except sqlite3.Error as e:
            logger.error(f"[SqliteLogger] log_new_agent error: {e}")

    def log_new_wrapper(self, wrapper: OpenAIWrapper, init_args: Dict) -> None:
        if self.con is None:
            return

        args = to_dict(
            init_args, exclude=("self", "__class__", "api_key", "organization", "base_url", "azure_endpoint")
        )

        query = """
        INSERT INTO oai_wrappers (wrapper_id, session_id, init_args, timestamp) VALUES (?, ?, ?, ?)
        ON CONFLICT (wrapper_id, session_id) DO NOTHING;
        """
        try:
            self.cur.execute(
                query,
                (
                    id(wrapper),
                    this._session_id,
                    json.dumps(args),
                    get_current_ts(),
                ),
            )
            self.con.commit()
        except sqlite3.Error as e:
            logger.error(f"[SqliteLogger] log_new_wrapper error: {e}")

    def log_new_client(self, client: Union[AzureOpenAI, OpenAI], wrapper: OpenAIWrapper, init_args: Dict) -> None:
        if self.con is None:
            return

        args = to_dict(
            init_args, exclude=("self", "__class__", "api_key", "organization", "base_url", "azure_endpoint")
        )

        query = """
        INSERT INTO oai_clients (client_id, wrapper_id, session_id, class, init_args, timestamp) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (client_id, session_id) DO NOTHING;
        """
        try:
            self.cur.execute(
                query,
                (
                    id(client),
                    id(wrapper),
                    this._session_id,
                    type(client).__name__,
                    json.dumps(args),
                    get_current_ts(),
                ),
            )
            self.con.commit()
        except sqlite3.Error as e:
            logger.error(f"[SqliteLogger] log_new_client error: {e}")

    def stop(self) -> None:
        if self.con:
            self.con.close()
            self.con = None
            self.cur = None

    def get_connection(self) -> sqlite3.Connection:
        if self.con:
            return self.con
