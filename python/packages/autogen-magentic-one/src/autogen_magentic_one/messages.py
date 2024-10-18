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

# the below are message types used in MagenticOne


# used by all agents to send messages
class BroadcastMessage(BaseModel):
    content: LLMMessage
    request_halt: bool = False


# used by orchestrator to obtain a response from an agent
@dataclass
class RequestReplyMessage:
    pass


# used by orchestrator to reset an agent
@dataclass
class ResetMessage:
    pass


# used by orchestrator to deactivate an agent
@dataclass
class DeactivateMessage:
    pass


# orchestrator events
@dataclass
class OrchestrationEvent:
    source: str
    message: str


MagenticOneMessages = RequestReplyMessage | BroadcastMessage | ResetMessage | DeactivateMessage


@dataclass
class AgentEvent:
    source: str
    message: str


# used by the web surfer agent
@dataclass
class WebSurferEvent:
    source: str
    message: str
    url: str
    action: str | None = None
    arguments: Dict[str, Any] | None = None
