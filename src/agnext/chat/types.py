from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Union

from agnext.components.image import Image
from agnext.components.llm import FunctionExecutionResultMessage
from agnext.components.types import FunctionCall


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


Message = Union[TextMessage, MultiModalMessage, FunctionCallMessage, FunctionExecutionResultMessage]


class ResponseFormat(Enum):
    text = "text"
    json_object = "json_object"


@dataclass
class RespondNow:
    response_format: ResponseFormat = field(default=ResponseFormat.text)


class Reset: ...
