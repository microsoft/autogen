from __future__ import annotations

import datetime
import inspect
import json
import logging
import openai
import os
import sqlite3
import sys
import uuid

from typing import TYPE_CHECKING, Any, Dict, List, Union, Tuple
from openai import OpenAI, AzureOpenAI
from openai.types.chat import ChatCompletion

if TYPE_CHECKING:
    from autogen import ConversableAgent, OpenAIWrapper

# this is a pointer to the module object instance itself
this = sys.modules[__name__]
this._session_id = None
this._con = None
this._cur = None
logger = logging.getLogger(__name__)


def start_logging(dbpath: str = "telemetry.db") -> str:
    """
    Open a connection to the telemetry logging database, and start recording.
    """
    this._session_id = str(uuid.uuid4())

    try:
        this._con = sqlite3.connect(dbpath)
        this._cur = this._con.cursor()

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
        this._cur.execute(query)
        this._con.commit()

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
        this._cur.execute(query)
        this._con.commit()

        query = """
            CREATE TABLE IF NOT EXISTS oai_wrappers (
                id INTEGER PRIMARY KEY,                             -- Key assigned by the database
                wrapper_id INTEGER,                                 -- result of python id(wrapper)
                session_id TEXT,
                init_args TEXT,                                     -- JSON serialization of constructor
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(wrapper_id, session_id))
        """
        this._cur.execute(query)
        this._con.commit()

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
        this._cur.execute(query)
        this._con.commit()

        query = """
        CREATE TABLE IF NOT EXISTS version (
            id INTEGER PRIMARY KEY CHECK (id = 1),                  -- id of the telemetry database
            version_number INTEGER NOT NULL                         -- version of the telemetry database
        );
        """
        this._cur.execute(query)
        this._con.commit

        current_verion = _get_current_version()
        if current_verion is None:
            query = """INSERT INTO version (id, version_number) VALUES (1, 1);"""
            this._cur.execute(query)
            this._con.commit

        _apply_migration(dbpath)

    except sqlite3.Error as e:
        logger.error(f"[Telemetry] start_logging error: {e}")
    finally:
        return this._session_id


def _get_current_version():
    this._cur.execute("SELECT version_number FROM version ORDER BY id DESC LIMIT 1")
    result = this._cur.fetchone()
    return result[0] if result else None


# Example migration script name format: 002_update_agents_table.sql
def _apply_migration(db_path, migrations_dir="./migrations"):
    current_version = _get_current_version()
    if os.path.isdir(migrations_dir):
        migrations = sorted(os.listdir(migrations_dir))
    else:
        logger.info("no migration scripts, skip...")
        return

    migrations_to_apply = [m for m in migrations if int(m.split("_")[0]) > current_version]

    for script in migrations_to_apply:
        with open(script, "r") as f:
            migration_sql = f.read()
            this._con.executescript(migration_sql)
            this._con.commit()

            latest_version = int(script.split("_")[0])
            this._cur.execute("UPDATE version SET version_number = ? WHERE id = 1", (latest_version))
            this._con.commit()


def get_connection():
    """
    Return a connection to the telemetry database.
    """
    return this._con


def _to_dict(
    obj: Union[int, float, str, bool, Dict[Any, Any], List[Any], Tuple[Any, ...], Any],
    exclude: Tuple[str] = (),
    no_recursive: Tuple[str] = (),
) -> Any:
    if isinstance(obj, (int, float, str, bool)):
        return obj
    elif callable(obj):
        return inspect.getsource(obj).strip()
    elif isinstance(obj, dict):
        return {
            str(k): _to_dict(str(v)) if isinstance(v, no_recursive) else _to_dict(v, exclude, no_recursive)
            for k, v in obj.items()
            if k not in exclude
        }
    elif isinstance(obj, (list, tuple)):
        return [_to_dict(str(v)) if isinstance(v, no_recursive) else _to_dict(v, exclude, no_recursive) for v in obj]
    elif hasattr(obj, "__dict__"):
        return {
            str(k): _to_dict(str(v)) if isinstance(v, no_recursive) else _to_dict(v, exclude, no_recursive)
            for k, v in vars(obj).items()
            if k not in exclude
        }
    else:
        return obj


def log_chat_completion(
    invocation_id: uuid.UUID,
    client_id: int,
    wrapper_id: int,
    request: Dict,
    response: Union[str, ChatCompletion],
    is_cached: int,
    cost: float,
    start_time: str,
) -> None:
    """
    Log a chat completion to the telemetry database.

    In AutoGen, chat completions are somewhat complicated because they are handled by the `autogen.oai.OpenAIWrapper` class.
    One invocation to `create` can lead to multiple underlying OpenAI calls, depending on the llm_config list used, and
    any errors or retries.

    Args:
        invocation_id (uuid):               A unique identifier for the invocation to the OpenAIWrapper.create method call
        client_id (int):                    A unique identifier for the underlying OpenAI client instance
        wrapper_id (int):                   A unique identifier for the OpenAIWrapper instance
        request (dict):                     A dictionary representing the the request or call to the OpenAI client endpoint
        response (str or ChatCompletion):   The response from OpenAI
        is_chached (int):                   1 if the response was a cache hit, 0 otherwise
        cost(float):                        The cost for OpenAI response
        start_time (str):                   A string representing the moment the request was initiated
    """

    if this._con is None:
        return

    end_time = get_current_ts()

    if isinstance(response, ChatCompletion):
        response_messages = json.dumps(_to_dict(response), indent=4)
    elif isinstance(response, dict):
        response_messages = json.dumps(response, indent=4)
    elif response is None or isinstance(response, str):
        response_messages = json.dumps({"response": response})
    else:
        raise TypeError("invalid type of response")

    query = """INSERT INTO chat_completions (
        invocation_id, client_id, wrapper_id, session_id, request, response, is_cached, cost, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    try:
        this._cur.execute(
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
        this._con.commit()
    except sqlite3.Error as e:
        logger.error(f"[Telemetry] log_chat_completion error: {e}")


def log_new_agent(agent: ConversableAgent, init_args: Dict):
    """
    Log the birth of a new agent.

    Args:
        agent (ConversableAgent):   The agent to log.
        init_args (dict):           The arguments passed to the construct the conversable agent
    """
    from autogen import Agent

    if this._con is None:
        return

    args = _to_dict(init_args, exclude=("self", "__class__", "api_key", "organization"), no_recursive=(Agent))

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
        this._cur.execute(
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
        this._con.commit()
    except sqlite3.Error as e:
        logger.error(f"[Telemetry] log_new_agent error: {e}")


def log_new_wrapper(wrapper: OpenAIWrapper, init_args: Dict):
    """
    Log the birth of a new OpenAIWrapper.

    Args:
        wrapper (OpenAIWrapper):    The wrapper to log.
        init_args (dict):           The arguments passed to the construct the wrapper
    """

    if this._con is None:
        return

    args = _to_dict(init_args, exclude=("self", "__class__", "api_key", "organization"))

    query = """
    INSERT INTO oai_wrappers (wrapper_id, session_id, init_args, timestamp) VALUES (?, ?, ?, ?)
    ON CONFLICT (wrapper_id, session_id) DO NOTHING;
    """
    try:
        this._cur.execute(
            query,
            (
                id(wrapper),
                this._session_id,
                json.dumps(args),
                get_current_ts(),
            ),
        )
        this._con.commit()
    except sqlite3.Error as e:
        logger.error(f"[Telemetry] log_new_wrapper error: {e}")


def log_new_client(client: Union[AzureOpenAI, OpenAI], wrapper: OpenAIWrapper, init_args: Dict):
    """
    Log the birth of a new OpenAIWrapper.

    Args:
        wrapper (OpenAI):           The OpenAI client to log.
        init_args (dict):           The arguments passed to the construct the client
    """

    if this._con is None:
        return

    args = _to_dict(init_args, exclude=("self", "__class__", "api_key", "organization"))

    query = """
    INSERT INTO oai_clients (client_id, wrapper_id, session_id, class, init_args, timestamp) VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT (client_id, session_id) DO NOTHING;
    """
    try:
        this._cur.execute(
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
        this._con.commit()
    except sqlite3.Error as e:
        logger.error(f"[Telemetry] log_new_client error: {e}")


def get_current_ts():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")


def stop_logging():
    """
    Close the connection to the telemetry database, and stop logging.
    """
    if this._con:
        this._con.close()
        this._con = None
        this._cur = None


def get_log(dbpath: str = "telemetry.db", table: str = "chat_completions") -> List[Dict]:
    """
    Return a dict string of the database.
    """
    con = sqlite3.connect(dbpath)
    query = f"SELECT * FROM {table}"
    cursor = con.execute(query)
    rows = cursor.fetchall()
    column_names = [description[0] for description in cursor.description]
    data = [dict(zip(column_names, row)) for row in rows]
    con.close()
    return data
