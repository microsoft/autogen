from __future__ import annotations

import datetime
import inspect
import json
import sqlite3
import sys
import uuid

from typing import TYPE_CHECKING, Any, Dict, List, Union, Tuple

if TYPE_CHECKING:
    from autogen import ConversableAgent, OpenAIWrapper

try:
    import openai
except ImportError:
    ERROR = ImportError("Please install openai>=1 and diskcache to use autogen.OpenAIWrapper.")
    OpenAI = object
    AzureOpenAI = object
else:
    from openai import OpenAI, AzureOpenAI
    from openai.types.chat import ChatCompletion

    ERROR = None

# this is a pointer to the module object instance itself
this = sys.modules[__name__]
this._session_id = str(uuid.uuid4())
this._con = None
this._cur = None


def start_logging(dbname: str = "telemetry.db") -> None:
    """
    Open a connection to the telemetry logging database, and start recording.
    """
    this._con = sqlite3.connect(dbname)
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


def get_connection():
    """
    Return a connection to the telemetry database.
    """
    return this._con


def _to_dict(
    obj: Union[int, float, str, bool, Dict[Any, Any], List[Any], Tuple[Any, ...], Any], exclude: List[str] = []
) -> Any:
    if isinstance(obj, (int, float, str, bool)):
        return obj
    elif callable(obj):
        return inspect.getsource(obj).strip()
    elif isinstance(obj, dict):
        return {k: _to_dict(v, exclude) for k, v in obj.items() if k not in exclude}
    elif isinstance(obj, (list, tuple)):
        return [_to_dict(v, exclude) for v in obj]
    elif hasattr(obj, "__dict__"):
        return {k: _to_dict(v, exclude) for k, v in vars(obj).items() if k not in exclude}
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

    # Nothing to do
    if this._con is None:
        return

    end_time = get_current_ts()

    if ERROR:
        raise ERROR

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


def log_new_agent(agent: ConversableAgent, init_args: Dict):
    """
    Log the birth of a new agent.

    Args:
        agent (ConversableAgent):   The agent to log.
        init_args (dict):           The arguments passed to the construct the conversable agent
    """

    if this._con is None:
        return

    if ERROR:
        raise ERROR

    args = _to_dict(init_args, exclude=["self", "__class__", "api_key", "organization"])

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

    this._cur.execute(
        query,
        (
            id(agent),
            agent.client.wrapper_id if agent.client is not None else "",
            this._session_id,
            agent.name,
            type(agent).__name__,
            json.dumps(args),
            get_current_ts(),
        ),
    )
    this._con.commit()


def log_new_wrapper(wrapper: OpenAIWrapper, init_args: Dict):
    """
    Log the birth of a new OpenAIWrapper.

    Args:
        wrapper (OpenAIWrapper):    The wrapper to log.
        init_args (dict):           The arguments passed to the construct the wrapper
    """

    if this._con is None:
        return

    if ERROR:
        raise ERROR

    args = _to_dict(init_args, exclude=["self", "__class__", "api_key", "organization"])

    query = """
    INSERT INTO oai_wrappers (wrapper_id, session_id, init_args, timestamp) VALUES (?, ?, ?, ?)
    ON CONFLICT (wrapper_id, session_id) DO NOTHING;
    """
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


def log_new_client(client: Union[AzureOpenAI, OpenAI], wrapper: OpenAIWrapper, init_args: Dict):
    """
    Log the birth of a new OpenAIWrapper.

    Args:
        wrapper (OpenAI):           The OpenAI client to log.
        init_args (dict):           The arguments passed to the construct the client
    """

    if this._con is None:
        return

    if ERROR:
        raise ERROR

    args = _to_dict(init_args, exclude=["self", "__class__", "api_key", "organization"])

    query = """
    INSERT INTO oai_clients (client_id, wrapper_id, session_id, class, init_args, timestamp) VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT (client_id, session_id) DO NOTHING;
    """

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
