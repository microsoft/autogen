from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Union

from openai.types.beta import AssistantResponseFormatParam

from agnext.agent_components.image import Image
from agnext.agent_components.types import FunctionCall


@dataclass(kw_only=True)
class BaseMessage:
    # Name of the agent that sent this message
    source: str


@dataclass
class TextMessage(BaseMessage):
    content: str


@dataclass
class MultiModalMessage(BaseMessage):
    content: List[Union[str, Image]]


@dataclass
class FunctionCallMessage(BaseMessage):
    content: List[FunctionCall]


@dataclass
class FunctionExecutionResult:
    content: str
    call_id: str


@dataclass
class FunctionExecutionResultMessage(BaseMessage):
    content: List[FunctionExecutionResult]


Message = Union[TextMessage, MultiModalMessage, FunctionCallMessage, FunctionExecutionResultMessage]


@dataclass
class RespondNow:
    response_format: Union[Literal["none", "auto"], AssistantResponseFormatParam] = "auto"


class Reset: ...
