from __future__ import annotations

import json
import logging
import os
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Union

from openai import AzureOpenAI, OpenAI
from openai.types.chat import ChatCompletion

from autogen.logger.base_logger import BaseLogger
from autogen.logger.logger_utils import get_current_ts, to_dict

from .base_logger import LLMConfig

if TYPE_CHECKING:
    from autogen import Agent, ConversableAgent, OpenAIWrapper

logger = logging.getLogger(__name__)


class FileLogger(BaseLogger):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.session_id = str(uuid.uuid4())
        self.log_file = self.config.get("filename", "runtime.log")

        log_dir = os.path.dirname(self.log_file)
        os.makedirs(log_dir, exist_ok=True)
        if not os.path.exists(self.log_file):
            open(self.log_file, "a").close()

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(self.log_file)
        self.logger.addHandler(file_handler)

    def start(self) -> str:
        try:
            self.logger.info(self.session_id)
        except Exception as e:
            self.logger.error(f"[file_logger] Failed to create logging file: {e}")
            raise e
        finally:
            return self.session_id

    def log_chat_completion(
        self,
        invocation_id: uuid.UUID,
        client_id: int,
        wrapper_id: int,
        request: Dict[str, Union[float, str, List[Dict[str, str]]]],
        response: Union[str, ChatCompletion],
        is_cached: int,
        cost: float,
        start_time: str,
    ) -> None:
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
                }
            )

            self.logger.info(log_data)
        except Exception as e:
            self.logger.error(f"[file_logger] Failed to log chat completion: {e}")

    def log_new_agent(self, agent: ConversableAgent, init_args: Dict[str, Any]) -> None:
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
                }
            )
            self.logger.info(log_data)
        except Exception as e:
            self.logger.error(f"[file_logger] Failed to log new agent: {e}")

    def log_event(self, source: Union[str, Agent], name: str, **kwargs: Dict[str, Any]) -> None:
        """"""
        from autogen import Agent

        json_args = json.dumps(kwargs, default=lambda o: f"<<non-serializable: {type(o).__qualname__}>>")

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
                    }
                )
                self.logger.info(log_data)
            except Exception as e:
                self.logger.error(f"[file_logger] Failed to log event {e}")

    def log_new_wrapper(self, wrapper: OpenAIWrapper, init_args: Dict[str, Union[LLMConfig, List[LLMConfig]]]) -> None:
        """"""
        try:
            log_data = json.dumps(
                {
                    "wrapper_id": id(wrapper),
                    "session_id": self.session_id,
                    "json_state": json.dumps(init_args),
                    "timestamp": get_current_ts(),
                }
            )
            self.logger.info(log_data)
        except Exception as e:
            self.logger.error(f"[file_logger] Failed to log event {e}")

    def log_new_client(self, client: AzureOpenAI | OpenAI, wrapper: OpenAIWrapper, init_args: Dict[str, Any]) -> None:
        try:
            log_data = json.dumps(
                {
                    "client_id": id(client),
                    "wrapper_id": id(wrapper),
                    "session_id": self.session_id,
                    "class": type(client).__name__,
                    "json_state": json.dumps(init_args),
                    "timestamp": get_current_ts(),
                }
            )
            self.logger.info(log_data)
        except Exception as e:
            self.logger.error(f"[file_logger] Failed to log event {e}")

    def get_connection(self) -> None:
        """Method is intentionally left blank because there is no specific connection needed for the FileLogger."""
        pass

    def stop(self) -> None:
        """Method is intentionally left blank because there is no specific shutdown needed for the FileLogger."""
        pass
