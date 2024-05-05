from __future__ import annotations

import json
import logging
import os
import threading
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
lock = threading.Lock()


class FileLogger(BaseLogger):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.session_id = str(uuid.uuid4())
        self.log_file = self.config.get("filename", "runtime.log")

    def start(self) -> str:
        try:
            with open(self.log_file, "a"):
                pass
        except Exception as e:
            logger.error(f"[file_logger] Failed to create logging file: {e}")
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
        with lock:
            try:
                with open(self.log_file, "a") as f:
                    f.write(
                        json.dumps(
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
                        + "\n"
                    )
            except Exception as e:
                logger.error(f"[file_logger] Failed to log chat completion: {e}")

    def log_new_agent(self, agent: ConversableAgent, init_args: Dict[str, Any]) -> None:
        with lock:
            try:
                with open(self.log_file, "a") as f:
                    f.write(
                        json.dumps(
                            {
                                "id": id(agent),
                                "agent_name": agent.name if hasattr(agent, "name") and agent.name is not None else "",
                                "wrapper_id": (
                                    agent.client.wrapper_id
                                    if hasattr(agent, "client") and agent.client is not None
                                    else ""
                                ),
                                "session_id": self.session_id,
                                "current_time": get_current_ts(),
                                "agent_type": type(agent).__name__,
                                "args": init_args,
                            }
                        )
                    )
            except Exception as e:
                logger.error(f"[file_logger] Failed to log new agent: {e}")

    def log_event(self, source: Union[str, Agent], name: str, **kwargs: Dict[str, Any]) -> None:
        """"""
        ...

    def log_new_wrapper(self, wrapper: OpenAIWrapper, init_args: Dict[str, Union[LLMConfig, List[LLMConfig]]]) -> None:
        """"""
        ...

    def log_new_client(self, client: AzureOpenAI | OpenAI, wrapper: OpenAIWrapper, init_args: Dict[str, Any]) -> None:
        return super().log_new_client(client, wrapper, init_args)

    def get_connection(self) -> None:
        pass

    def stop(self) -> None:
        """Method is intentionally left blank because there is no specific shutdown needed for the FileLogger."""
        pass
