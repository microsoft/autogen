from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

from openai import AzureOpenAI, OpenAI
from openai.types.chat import ChatCompletion

from autogen.logger.base_logger import BaseLogger
from autogen.logger.logger_utils import get_current_ts, to_dict

from .base_logger import LLMConfig

if TYPE_CHECKING:
    from autogen import Agent, ConversableAgent, OpenAIWrapper
    from autogen.oai.anthropic import AnthropicClient
    from autogen.oai.gemini import GeminiClient
    from autogen.oai.mistral import MistralAIClient
    from autogen.oai.together import TogetherClient

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

__all__ = ("FileLogger",)


def safe_serialize(obj: Any) -> str:
    def default(o: Any) -> str:
        if hasattr(o, "to_json"):
            return str(o.to_json())
        else:
            return f"<<non-serializable: {type(o).__qualname__}>>"

    return json.dumps(obj, default=default)


class FileLogger(BaseLogger):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.session_id = str(uuid.uuid4())

        curr_dir = os.getcwd()
        self.log_dir = os.path.join(curr_dir, "autogen_logs")
        os.makedirs(self.log_dir, exist_ok=True)

        self.log_file = os.path.join(self.log_dir, self.config.get("filename", "runtime.log"))
        try:
            with open(self.log_file, "a"):
                pass
        except Exception as e:
            logger.error(f"[file_logger] Failed to create logging file: {e}")

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(self.log_file)
        self.logger.addHandler(file_handler)

    def start(self) -> str:
        """Start the logger and return the session_id."""
        try:
            self.logger.info(f"Started new session with Session ID: {self.session_id}")
        except Exception as e:
            logger.error(f"[file_logger] Failed to create logging file: {e}")
        finally:
            return self.session_id

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
        """
        Log a chat completion.
        """
        thread_id = threading.get_ident()
        source_name = None
        if isinstance(source, str):
            source_name = source
        else:
            source_name = source.name
        try:
            log_data = json.dumps(
                {
                    "invocation_id": str(invocation_id),
                    "client_id": client_id,
                    "wrapper_id": wrapper_id,
                    "request": to_dict(request),
                    "response": str(response),
                    "is_cached": is_cached,
                    "cost": cost,
                    "start_time": start_time,
                    "end_time": get_current_ts(),
                    "thread_id": thread_id,
                    "source_name": source_name,
                }
            )

            self.logger.info(log_data)
        except Exception as e:
            self.logger.error(f"[file_logger] Failed to log chat completion: {e}")

    def log_new_agent(self, agent: ConversableAgent, init_args: Dict[str, Any] = {}) -> None:
        """
        Log a new agent instance.
        """
        thread_id = threading.get_ident()

        try:
            log_data = json.dumps(
                {
                    "id": id(agent),
                    "agent_name": agent.name if hasattr(agent, "name") and agent.name is not None else "",
                    "wrapper_id": to_dict(
                        agent.client.wrapper_id if hasattr(agent, "client") and agent.client is not None else ""
                    ),
                    "session_id": self.session_id,
                    "current_time": get_current_ts(),
                    "agent_type": type(agent).__name__,
                    "args": to_dict(init_args),
                    "thread_id": thread_id,
                }
            )
            self.logger.info(log_data)
        except Exception as e:
            self.logger.error(f"[file_logger] Failed to log new agent: {e}")

    def log_event(self, source: Union[str, Agent], name: str, **kwargs: Dict[str, Any]) -> None:
        """
        Log an event from an agent or a string source.
        """
        from autogen import Agent

        # This takes an object o as input and returns a string. If the object o cannot be serialized, instead of raising an error,
        # it returns a string indicating that the object is non-serializable, along with its type's qualified name obtained using __qualname__.
        json_args = json.dumps(kwargs, default=lambda o: f"<<non-serializable: {type(o).__qualname__}>>")
        thread_id = threading.get_ident()

        if isinstance(source, Agent):
            try:
                log_data = json.dumps(
                    {
                        "source_id": id(source),
                        "source_name": str(source.name) if hasattr(source, "name") else source,
                        "event_name": name,
                        "agent_module": source.__module__,
                        "agent_class": source.__class__.__name__,
                        "json_state": json_args,
                        "timestamp": get_current_ts(),
                        "thread_id": thread_id,
                    }
                )
                self.logger.info(log_data)
            except Exception as e:
                self.logger.error(f"[file_logger] Failed to log event {e}")
        else:
            try:
                log_data = json.dumps(
                    {
                        "source_id": id(source),
                        "source_name": str(source.name) if hasattr(source, "name") else source,
                        "event_name": name,
                        "json_state": json_args,
                        "timestamp": get_current_ts(),
                        "thread_id": thread_id,
                    }
                )
                self.logger.info(log_data)
            except Exception as e:
                self.logger.error(f"[file_logger] Failed to log event {e}")

    def log_new_wrapper(
        self, wrapper: OpenAIWrapper, init_args: Dict[str, Union[LLMConfig, List[LLMConfig]]] = {}
    ) -> None:
        """
        Log a new wrapper instance.
        """
        thread_id = threading.get_ident()

        try:
            log_data = json.dumps(
                {
                    "wrapper_id": id(wrapper),
                    "session_id": self.session_id,
                    "json_state": json.dumps(init_args),
                    "timestamp": get_current_ts(),
                    "thread_id": thread_id,
                }
            )
            self.logger.info(log_data)
        except Exception as e:
            self.logger.error(f"[file_logger] Failed to log event {e}")

    def log_new_client(
        self,
        client: AzureOpenAI | OpenAI | GeminiClient | AnthropicClient | MistralAIClient | TogetherClient,
        wrapper: OpenAIWrapper,
        init_args: Dict[str, Any],
    ) -> None:
        """
        Log a new client instance.
        """
        thread_id = threading.get_ident()

        try:
            log_data = json.dumps(
                {
                    "client_id": id(client),
                    "wrapper_id": id(wrapper),
                    "session_id": self.session_id,
                    "class": type(client).__name__,
                    "json_state": json.dumps(init_args),
                    "timestamp": get_current_ts(),
                    "thread_id": thread_id,
                }
            )
            self.logger.info(log_data)
        except Exception as e:
            self.logger.error(f"[file_logger] Failed to log event {e}")

    def log_function_use(self, source: Union[str, Agent], function: F, args: Dict[str, Any], returns: Any) -> None:
        """
        Log a registered function(can be a tool) use from an agent or a string source.
        """
        thread_id = threading.get_ident()

        try:
            log_data = json.dumps(
                {
                    "source_id": id(source),
                    "source_name": str(source.name) if hasattr(source, "name") else source,
                    "agent_module": source.__module__,
                    "agent_class": source.__class__.__name__,
                    "timestamp": get_current_ts(),
                    "thread_id": thread_id,
                    "input_args": safe_serialize(args),
                    "returns": safe_serialize(returns),
                }
            )
            self.logger.info(log_data)
        except Exception as e:
            self.logger.error(f"[file_logger] Failed to log event {e}")

    def get_connection(self) -> None:
        """Method is intentionally left blank because there is no specific connection needed for the FileLogger."""
        pass

    def stop(self) -> None:
        """Close the file handler and remove it from the logger."""
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.logger.removeHandler(handler)
