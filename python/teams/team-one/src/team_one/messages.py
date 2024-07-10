from dataclasses import dataclass
from typing import List, Union

from agnext.components import FunctionCall, Image
from agnext.components.models import FunctionExecutionResult, LLMMessage

# Convenience type
UserContent = Union[str, List[Union[str, Image]]]
AssistantContent = Union[str, List[FunctionCall]]
FunctionExecutionContent = List[FunctionExecutionResult]
SystemContent = str


@dataclass
class BroadcastMessage:
    content: LLMMessage
    request_halt: bool = False


@dataclass
class RequestReplyMessage:
    pass


@dataclass
class OrchestrationEvent:
    source: str
    message: str
