from __future__ import annotations

import logging
import sqlite3
import uuid
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional, TypeVar, Union

from openai import AzureOpenAI, OpenAI
from openai.types.chat import ChatCompletion

from autogen.logger.base_logger import BaseLogger, LLMConfig
from autogen.logger.logger_factory import LoggerFactory

if TYPE_CHECKING:
    from autogen import Agent, ConversableAgent, OpenAIWrapper
    from autogen.oai.anthropic import AnthropicClient
    from autogen.oai.gemini import GeminiClient

logger = logging.getLogger(__name__)

autogen_logger = None
is_logging = False

F = TypeVar("F", bound=Callable[..., Any])


def start(
    logger: Optional[BaseLogger] = None,
    logger_type: Literal["sqlite", "file"] = "sqlite",
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Start logging for the runtime.
    Args:
        logger (BaseLogger):    A logger instance
        logger_type (str):      The type of logger to use (default: sqlite)
        config (dict):          Configuration for the logger
    Returns:
        session_id (str(uuid.uuid4)):       a unique id for the logging session
    """
    global autogen_logger
    global is_logging

    if logger:
        autogen_logger = logger
    else:
        autogen_logger = LoggerFactory.get_logger(logger_type=logger_type, config=config)

    try:
        session_id = autogen_logger.start()
        is_logging = True
    except Exception as e:
        logger.error(f"[runtime logging] Failed to start logging: {e}")
    finally:
        return session_id


def log_chat_completion(
    invocation_id: uuid.UUID,
    client_id: int,
    wrapper_id: int,
    agent: Union[str, Agent],
    request: Dict[str, Union[float, str, List[Dict[str, str]]]],
    response: Union[str, ChatCompletion],
    is_cached: int,
    cost: float,
    start_time: str,
) -> None:
    if autogen_logger is None:
        logger.error("[runtime logging] log_chat_completion: autogen logger is None")
        return

    autogen_logger.log_chat_completion(
        invocation_id, client_id, wrapper_id, agent, request, response, is_cached, cost, start_time
    )


def log_new_agent(agent: ConversableAgent, init_args: Dict[str, Any]) -> None:
    if autogen_logger is None:
        logger.error("[runtime logging] log_new_agent: autogen logger is None")
        return

    autogen_logger.log_new_agent(agent, init_args)


def log_event(source: Union[str, Agent], name: str, **kwargs: Dict[str, Any]) -> None:
    if autogen_logger is None:
        logger.error("[runtime logging] log_event: autogen logger is None")
        return

    autogen_logger.log_event(source, name, **kwargs)


def log_function_use(agent: Union[str, Agent], function: F, args: Dict[str, Any], returns: any):
    if autogen_logger is None:
        logger.error("[runtime logging] log_function_use: autogen logger is None")
        return

    autogen_logger.log_function_use(agent, function, args, returns)


def log_new_wrapper(wrapper: OpenAIWrapper, init_args: Dict[str, Union[LLMConfig, List[LLMConfig]]]) -> None:
    if autogen_logger is None:
        logger.error("[runtime logging] log_new_wrapper: autogen logger is None")
        return

    autogen_logger.log_new_wrapper(wrapper, init_args)


def log_new_client(
    client: Union[AzureOpenAI, OpenAI, GeminiClient, AnthropicClient], wrapper: OpenAIWrapper, init_args: Dict[str, Any]
) -> None:
    if autogen_logger is None:
        logger.error("[runtime logging] log_new_client: autogen logger is None")
        return

    autogen_logger.log_new_client(client, wrapper, init_args)


def stop() -> None:
    global is_logging
    if autogen_logger:
        autogen_logger.stop()
    is_logging = False


def get_connection() -> Union[None, sqlite3.Connection]:
    if autogen_logger is None:
        logger.error("[runtime logging] get_connection: autogen logger is None")
        return None

    return autogen_logger.get_connection()


def logging_enabled() -> bool:
    return is_logging
