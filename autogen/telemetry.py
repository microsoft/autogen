import sqlite3
import datetime
import json
import uuid
import sys
import copy

try:
    import openai
    from openai.types.chat import ChatCompletion

    ERROR = None
except ImportError:
    ERROR = ImportError("Please install openai>=1 and diskcache to use autogen.OpenAIWrapper.")

# this is a pointer to the module object instance itself
this = sys.modules[__name__]
this._session_id = str(uuid.uuid4())
this._con = None
this._cur = None


def start_logging(dbname="telemetry.db"):
    """
    Open a connection to the telemetry logging database, and start recording.
    """
    this._con = sqlite3.connect(dbname)
    this._cur = this._con.cursor()
    this._session_id = str(uuid.uuid4())
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
            client_config TEXT,
            cost REAL,
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_time DATETIME DEFAULT CURRENT_TIMESTAMP)
    """
    this._cur.execute(query)

    query = """
        CREATE TABLE IF NOT EXISTS agents(
            id INTEGER PRIMARY KEY,
            wrapper_id INTEGER,
            session_id TEXT,
            name TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);
    """
    this._cur.execute(query)
    this._con.commit()


def get_connection():
    """
    Return a connection to the telemetry database.
    """
    return this._con


def _to_dict(obj, exclude=[]):
    if isinstance(obj, (int, float, str, bool)):
        return obj
    elif isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items() if k not in exclude}
    elif isinstance(obj, (list, tuple)):
        return [_to_dict(v) for v in obj]
    elif hasattr(obj, "__dict__"):
        return {k: _to_dict(v) for k, v in vars(obj).items() if k not in exclude}
    else:
        return obj


def log_chat_completion(invocation_id, client_id, wrapper_id, request, response, is_cached, client_config, cost, start_time):
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
        client_config (dict):               A dictionary representing the underlying OpenAI client configuration (model, etc.)
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
    elif isinstance(response, str):
        response_messages = json.dumps({"error": response})
    elif response is None:
        response_messages = ""
    else:
        raise "invalid type of response"

    # Sanitize the client_config
    _client_config = copy.deepcopy(client_config)
    for k in ["api_key", "organization"]:
        if k in _client_config:
            del _client_config[k]

    query = """INSERT INTO chat_completions (
        invocation_id, client_id, wrapper_id, session_id, request, response, is_cached, client_config, cost, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
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
            json.dumps(_client_config),
            cost,
            start_time,
            end_time,
        ),
    )
    this._con.commit()


def log_new_agent(agent, init_args):
    """
    Log the birth of a new agent.

    Args:
        agent (ConversableAgent):   The agent to log.
        init_args (dict):           The arguments passed to the construct the conversable agent
    """

    # Nothing to do
    if this._con is None:
        return

    if ERROR:
        raise ERROR

    print(_to_dict(init_args, exclude=["self", "__class__"]))

    # _client_config = copy.deepcopy(client_config)
    # for k in ["api_key", "organization"]:
    #    if k in _client_config:
    #        del _client_config[k]
    #
    # query = """INSERT INTO chat_completions (
    #    invocation_id, client_id, wrapper_id, session_id, request, response, is_cached, client_config, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    # this._cur.execute(
    #    query,
    #    (


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
