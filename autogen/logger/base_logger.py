from __future__ import annotations

import sqlite3
import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Union

from openai import AzureOpenAI, OpenAI
from openai.types.chat import ChatCompletion

if TYPE_CHECKING:
    from autogen import ConversableAgent, OpenAIWrapper

ConfigItem = Dict[str, Union[str, List[str]]]
LLMConfig = Dict[str, Union[None, float, int, ConfigItem, List[ConfigItem]]]


class BaseLogger(ABC):
    @abstractmethod
    def start(self) -> str:
        """
        Open a connection to the logging database, and start recording.

        Returns:
            session_id (str):     a unique id for the logging session
        """
        ...

    @abstractmethod
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
        """
        Log a chat completion to database.

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
        ...

    @abstractmethod
    def log_new_agent(self, agent: ConversableAgent, init_args: Dict[str, Any]) -> None:
        """
        Log the birth of a new agent.

        Args:
            agent (ConversableAgent):   The agent to log.
            init_args (dict):           The arguments passed to the construct the conversable agent
        """
        ...

    @abstractmethod
    def log_new_wrapper(self, wrapper: OpenAIWrapper, init_args: Dict[str, Union[LLMConfig, List[LLMConfig]]]) -> None:
        """
        Log the birth of a new OpenAIWrapper.

        Args:
            wrapper (OpenAIWrapper):    The wrapper to log.
            init_args (dict):           The arguments passed to the construct the wrapper
        """
        ...

    @abstractmethod
    def log_new_client(
        self, client: Union[AzureOpenAI, OpenAI], wrapper: OpenAIWrapper, init_args: Dict[str, Any]
    ) -> None:
        """
        Log the birth of a new OpenAIWrapper.

        Args:
            wrapper (OpenAI):           The OpenAI client to log.
            init_args (dict):           The arguments passed to the construct the client
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """
        Close the connection to the logging database, and stop logging.
        """
        ...

    @abstractmethod
    def get_connection(self) -> Union[None, sqlite3.Connection]:
        """
        Return a connection to the logging database.
        """
        ...
