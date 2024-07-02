from dataclasses import dataclass

from agnext.components.models import LLMMessage


@dataclass
class BroadcastMessage:
    content: LLMMessage


@dataclass
class RequestReplyMessage:
    pass


@dataclass
class OrchestrationEvent:
    timestamp: str
    message: str
