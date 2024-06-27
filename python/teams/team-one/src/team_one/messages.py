from dataclasses import dataclass
from agnext.components.models import FunctionExecutionResult
from agnext.components import FunctionCall


@dataclass
class ToolMessage:
    function_call: FunctionCall


@dataclass
class ToolResultMessage:
    result: FunctionExecutionResult


@dataclass
class TaskMessage:
    content: str


@dataclass
class LLMResponseMessage:
    content: str


@dataclass
class BroadcastMessage:
    content: str


@dataclass
class RequestReplyMessage:
    pass
