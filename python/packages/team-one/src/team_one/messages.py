from dataclasses import dataclass
from typing import Any, Dict, List, Union

from autogen_core.components import FunctionCall, Image
from autogen_core.components.models import FunctionExecutionResult, LLMMessage
from pydantic import BaseModel

# Convenience type
UserContent = Union[str, List[Union[str, Image]]]
AssistantContent = Union[str, List[FunctionCall]]
FunctionExecutionContent = List[FunctionExecutionResult]
SystemContent = str


class BroadcastMessage(BaseModel):
    content: LLMMessage
    request_halt: bool = False


@dataclass
class RequestReplyMessage:
    pass


@dataclass
class ResetMessage:
    pass


@dataclass
class DeactivateMessage:
    pass


@dataclass
class OrchestrationEvent:
    source: str
    message: str


TeamOneMessages = RequestReplyMessage | BroadcastMessage | ResetMessage | DeactivateMessage


@dataclass
class AgentEvent:
    source: str
    message: str


@dataclass
class WebSurferEvent:
    source: str
    message: str
    url: str
    action: str | None = None
    arguments: Dict[str, Any] | None = None
