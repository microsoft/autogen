from dataclasses import dataclass

from agnext.components.models import LLMMessage


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
