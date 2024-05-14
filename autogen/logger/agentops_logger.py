from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Union, TypeVar, Callable

import agentops
from openai import AzureOpenAI, OpenAI
from openai.types.chat import ChatCompletion

from autogen.logger.base_logger import BaseLogger
from autogen.logger.logger_utils import get_current_ts, to_dict

from .base_logger import LLMConfig

from agentops import LLMEvent, ToolEvent, ActionEvent
from uuid import uuid4

if TYPE_CHECKING:
    from autogen import Agent, ConversableAgent, OpenAIWrapper

logger = logging.getLogger(__name__)
lock = threading.Lock()

__all__ = ("AgentOpsLogger",)

F = TypeVar("F", bound=Callable[..., Any])


class AgentOpsLogger(BaseLogger):
    agent_store: [{"agentops_id": str, "autogen_id": str}] = []

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def start(self) -> str:
        pass

    def _get_agentops_id_from_agent(self, autogen_id: str) -> str:
        for agent in self.agent_store:
            if agent["autogen_id"] == autogen_id:
                return agent["agentops_id"]

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
        end_time = get_current_ts()

        completion = response.choices[len(response.choices)-1]

        llm_event = LLMEvent(prompt=request['messages'], completion=completion.message, model=response.model)
        llm_event.init_timestamp = start_time
        llm_event.end_timestamp = end_time
        llm_event.agent_id = self._get_agentops_id_from_agent(str(id(source)))
        agentops.record(llm_event)

    def log_new_agent(self, agent: ConversableAgent, init_args: Dict[str, Any]) -> None:
        ao_agent_id = agentops.create_agent(agent.name, str(uuid4()))
        self.agent_store.append({'agentops_id': ao_agent_id, 'autogen_id': str(id(agent))})

    def log_event(self, source: Union[str, Agent], name: str, **kwargs: Dict[str, Any]) -> None:
        event = ActionEvent(action_type=name)
        agentops_id = self._get_agentops_id_from_agent(str(id(source)))
        event.agent_id = agentops_id
        agentops.record(event)

    def log_function_use(
            self, source: Union[str, Agent], function: F, args: Dict[str, Any], returns: any
    ):
        event = ToolEvent()
        agentops_id = self._get_agentops_id_from_agent(str(id(source)))
        event.agent_id = agentops_id
        event.function = function
        event.params = args
        event.returns = returns
        event.name = getattr(function, '_name')
        agentops.record(event)

    def log_new_wrapper(self, wrapper: OpenAIWrapper, init_args: Dict[str, Union[LLMConfig, List[LLMConfig]]]) -> None:
        pass

    def log_new_client(
        self, client: Union[AzureOpenAI, OpenAI], wrapper: OpenAIWrapper, init_args: Dict[str, Any]
    ) -> None:
        pass

    def stop(self) -> None:
        if self.con:
            self.con.close()

    def get_connection(self) -> Union[None, sqlite3.Connection]:
        if self.con:
            return self.con
        return None
