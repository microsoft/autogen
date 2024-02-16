from __future__ import annotations

from autogen.logger.logger_factory import LoggerFactory
import sqlite3
from typing import Any, Dict, Optional, TYPE_CHECKING, Union
import uuid

from openai import OpenAI, AzureOpenAI
from openai.types.chat import ChatCompletion

if TYPE_CHECKING:
    from autogen import ConversableAgent, OpenAIWrapper

autogen_logger = None
is_logging = False


def start(logger_type: str = "sqlite", config: Optional[Dict[str, Any]] = None) -> str:
    global autogen_logger
    global is_logging

    if autogen_logger is None:
        autogen_logger = LoggerFactory.get_logger(logger_type=logger_type, config=config)

    session_id = autogen_logger.start()
    is_logging = True

    return session_id


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
    autogen_logger.log_chat_completion(
        invocation_id, client_id, wrapper_id, request, response, is_cached, cost, start_time
    )


def log_new_agent(agent: ConversableAgent, init_args: Dict) -> None:
    autogen_logger.log_new_agent(agent, init_args)


def log_new_wrapper(wrapper: OpenAIWrapper, init_args: Dict) -> None:
    autogen_logger.log_new_wrapper(wrapper, init_args)


def log_new_client(client: Union[AzureOpenAI, OpenAI], wrapper: OpenAIWrapper, init_args: Dict) -> None:
    autogen_logger.log_new_client(client, wrapper, init_args)


def stop() -> None:
    global is_logging
    if autogen_logger:
        autogen_logger.stop()
    is_logging = False


def get_connection() -> Union[sqlite3.Connection]:
    return autogen_logger.get_connection()


def logging_enabled() -> bool:
    return is_logging
