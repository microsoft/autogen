from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import uuid
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Tuple, TypeVar, Union

from openai import AzureOpenAI, OpenAI
from openai.types.chat import ChatCompletion

from autogen.logger.base_logger import BaseLogger
from autogen.logger.logger_utils import get_current_ts, to_dict

from .base_logger import LLMConfig

if TYPE_CHECKING:
    from autogen import Agent, ConversableAgent, OpenAIWrapper
    from autogen.oai.anthropic import AnthropicClient
    from autogen.oai.cohere import CohereClient
    from autogen.oai.gemini import GeminiClient
    from autogen.oai.groq import GroqClient
    from autogen.oai.mistral import MistralAIClient
    from autogen.oai.together import TogetherClient

logger = logging.getLogger(__name__)
lock = threading.Lock()

__all__ = ("SqliteLogger",)

F = TypeVar("F", bound=Callable[..., Any])


def safe_serialize(obj: Any) -> str:
    def default(o: Any) -> str:
        if hasattr(o, "to_json"):
            return str(o.to_json())
        else:
            return f"<<non-serializable: {type(o).__qualname__}>>"

    return json.dumps(obj, default=default)


class SqliteLogger(BaseLogger):
    schema_version = 1

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        try:
            self.dbname = self.config.get("dbname", "logs.db")
            self.con = sqlite3.connect(self.dbname, check_same_thread=False)
            self.cur = self.con.cursor()
            self.session_id = str(uuid.uuid4())
        except sqlite3.Error as e:
            logger.error(f"[SqliteLogger] Failed to connect to database {self.dbname}: {e}")

    def start(self) -> str:
        try:
            query = """
                CREATE TABLE IF NOT EXISTS chat_completions(
                    id INTEGER PRIMARY KEY,
                    invocation_id TEXT,
                    client_id INTEGER,
                    wrapper_id INTEGER,
                    session_id TEXT,
                    source_name TEXT,
                    request TEXT,
                    response TEXT,
                    is_cached INEGER,
                    cost REAL,
                    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    end_time DATETIME DEFAULT CURRENT_TIMESTAMP)
            """
            self._run_query(query=query)

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
            self._run_query(query=query)

            query = """
                CREATE TABLE IF NOT EXISTS oai_wrappers (
                    id INTEGER PRIMARY KEY,                             -- Key assigned by the database
                    wrapper_id INTEGER,                                 -- result of python id(wrapper)
                    session_id TEXT,
                    init_args TEXT,                                     -- JSON serialization of constructor
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(wrapper_id, session_id))
            """
            self._run_query(query=query)

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
            self._run_query(query=query)

            query = """
            CREATE TABLE IF NOT EXISTS version (
                id INTEGER PRIMARY KEY CHECK (id = 1),                  -- id of the logging database
                version_number INTEGER NOT NULL                         -- version of the logging database
            );
            """
            self._run_query(query=query)

            query = """
            CREATE TABLE IF NOT EXISTS events (
                event_name TEXT,
                source_id INTEGER,
                source_name TEXT,
                agent_module TEXT DEFAULT NULL,
                agent_class_name TEXT DEFAULT NULL,
                id INTEGER PRIMARY KEY,
                json_state TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
            self._run_query(query=query)

            query = """
                        CREATE TABLE IF NOT EXISTS function_calls (
                            source_id INTEGER,
                            source_name TEXT,
                            function_name TEXT,
                            args TEXT DEFAULT NULL,
                            returns TEXT DEFAULT NULL,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                        );
                        """
            self._run_query(query=query)

            current_verion = self._get_current_db_version()
            if current_verion is None:
                self._run_query(
                    query="INSERT INTO version (id, version_number) VALUES (1, ?);", args=(SqliteLogger.schema_version,)
                )
            self._apply_migration()

        except sqlite3.Error as e:
            logger.error(f"[SqliteLogger] start logging error: {e}")
        finally:
            return self.session_id

    def _get_current_db_version(self) -> Union[None, int]:
        self.cur.execute("SELECT version_number FROM version ORDER BY id DESC LIMIT 1")
        result = self.cur.fetchone()
        return result[0] if result is not None else None

    # Example migration script name format: 002_update_agents_table.sql
    def _apply_migration(self, migrations_dir: str = "./migrations") -> None:
        current_version = self._get_current_db_version()
        current_version = SqliteLogger.schema_version if current_version is None else current_version

        if os.path.isdir(migrations_dir):
            migrations = sorted(os.listdir(migrations_dir))
        else:
            logger.info("no migration scripts, skip...")
            return

        migrations_to_apply = [m for m in migrations if int(m.split("_")[0]) > current_version]

        for script in migrations_to_apply:
            with open(script, "r") as f:
                migration_sql = f.read()
                self._run_query_script(script=migration_sql)

                latest_version = int(script.split("_")[0])
                query = "UPDATE version SET version_number = ? WHERE id = 1"
                args = (latest_version,)
                self._run_query(query=query, args=args)

    def _run_query(self, query: str, args: Tuple[Any, ...] = ()) -> None:
        """
        Executes a given SQL query.

        Args:
            query (str):        The SQL query to execute.
            args (Tuple):       The arguments to pass to the SQL query.
        """
        try:
            with lock:
                self.cur.execute(query, args)
                self.con.commit()
        except Exception as e:
            logger.error("[sqlite logger]Error running query with query %s and args %s: %s", query, args, e)

    def _run_query_script(self, script: str) -> None:
        """
        Executes SQL script.

        Args:
            script (str):       SQL script to execute.
        """
        try:
            with lock:
                self.cur.executescript(script)
                self.con.commit()
        except Exception as e:
            logger.error("[sqlite logger]Error running query script %s: %s", script, e)

    def log_chat_completion(
        self,
        invocation_id: uuid.UUID,
        client_id: int,
        wrapper_id: int,
        source: Union[str, Agent],
        request: Dict[str, Union[float, str, List[Dict[str, str]]]],
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

        source_name = None
        if isinstance(source, str):
            source_name = source
        else:
            source_name = source.name

        query = """
            INSERT INTO chat_completions (
                invocation_id, client_id, wrapper_id, session_id, request, response, is_cached, cost, start_time, end_time, source_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        args = (
            invocation_id,
            client_id,
            wrapper_id,
            self.session_id,
            json.dumps(request),
            response_messages,
            is_cached,
            cost,
            start_time,
            end_time,
            source_name,
        )

        self._run_query(query=query, args=args)

    def log_new_agent(self, agent: ConversableAgent, init_args: Dict[str, Any]) -> None:
        from autogen import Agent

        if self.con is None:
            return

        args = to_dict(
            init_args,
            exclude=(
                "self",
                "__class__",
                "api_key",
                "organization",
                "base_url",
                "azure_endpoint",
                "azure_ad_token",
                "azure_ad_token_provider",
            ),
            no_recursive=(Agent,),
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
        args = (
            id(agent),
            agent.client.wrapper_id if hasattr(agent, "client") and agent.client is not None else "",
            self.session_id,
            agent.name if hasattr(agent, "name") and agent.name is not None else "",
            type(agent).__name__,
            json.dumps(args),
            get_current_ts(),
        )
        self._run_query(query=query, args=args)

    def log_event(self, source: Union[str, Agent], name: str, **kwargs: Dict[str, Any]) -> None:
        from autogen import Agent

        if self.con is None:
            return

        json_args = json.dumps(kwargs, default=lambda o: f"<<non-serializable: {type(o).__qualname__}>>")

        if isinstance(source, Agent):
            query = """
            INSERT INTO events (source_id, source_name, event_name, agent_module, agent_class_name, json_state, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            args = (
                id(source),
                source.name if hasattr(source, "name") else source,
                name,
                source.__module__,
                source.__class__.__name__,
                json_args,
                get_current_ts(),
            )
            self._run_query(query=query, args=args)
        else:
            query = """
            INSERT INTO events (source_id, source_name, event_name, json_state, timestamp) VALUES (?, ?, ?, ?, ?)
            """
            args_str_based = (
                id(source),
                source.name if hasattr(source, "name") else source,
                name,
                json_args,
                get_current_ts(),
            )
            self._run_query(query=query, args=args_str_based)

    def log_new_wrapper(self, wrapper: OpenAIWrapper, init_args: Dict[str, Union[LLMConfig, List[LLMConfig]]]) -> None:
        if self.con is None:
            return

        args = to_dict(
            init_args,
            exclude=(
                "self",
                "__class__",
                "api_key",
                "organization",
                "base_url",
                "azure_endpoint",
                "azure_ad_token",
                "azure_ad_token_provider",
            ),
        )

        query = """
        INSERT INTO oai_wrappers (wrapper_id, session_id, init_args, timestamp) VALUES (?, ?, ?, ?)
        ON CONFLICT (wrapper_id, session_id) DO NOTHING;
        """
        args = (
            id(wrapper),
            self.session_id,
            json.dumps(args),
            get_current_ts(),
        )
        self._run_query(query=query, args=args)

    def log_function_use(self, source: Union[str, Agent], function: F, args: Dict[str, Any], returns: Any) -> None:

        if self.con is None:
            return

        query = """
        INSERT INTO function_calls (source_id, source_name, function_name, args, returns, timestamp) VALUES (?, ?, ?, ?, ?, ?)
        """
        query_args: Tuple[Any, ...] = (
            id(source),
            source.name if hasattr(source, "name") else source,
            function.__name__,
            safe_serialize(args),
            safe_serialize(returns),
            get_current_ts(),
        )
        self._run_query(query=query, args=query_args)

    def log_new_client(
        self,
        client: Union[
            AzureOpenAI,
            OpenAI,
            GeminiClient,
            AnthropicClient,
            MistralAIClient,
            TogetherClient,
            GroqClient,
            CohereClient,
        ],
        wrapper: OpenAIWrapper,
        init_args: Dict[str, Any],
    ) -> None:
        if self.con is None:
            return

        args = to_dict(
            init_args,
            exclude=(
                "self",
                "__class__",
                "api_key",
                "organization",
                "base_url",
                "azure_endpoint",
                "azure_ad_token",
                "azure_ad_token_provider",
            ),
        )

        query = """
        INSERT INTO oai_clients (client_id, wrapper_id, session_id, class, init_args, timestamp) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (client_id, session_id) DO NOTHING;
        """
        args = (
            id(client),
            id(wrapper),
            self.session_id,
            type(client).__name__,
            json.dumps(args),
            get_current_ts(),
        )
        self._run_query(query=query, args=args)

    def stop(self) -> None:
        if self.con:
            self.con.close()

    def get_connection(self) -> Union[None, sqlite3.Connection]:
        if self.con:
            return self.con
        return None
