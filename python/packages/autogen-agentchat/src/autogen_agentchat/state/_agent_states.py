from dataclasses import dataclass, field
from typing import List

from autogen_core.components.models import (
    AssistantMessage,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)

from ._base import BaseState


@dataclass(kw_only=True)
class AssistantAgentState(BaseState):
    model_context: List[LLMMessage] = field(default_factory=list)
    state_type: str = field(default="AssistantAgentState")
    version: str = field(default="1.0.0")

    def __post_init__(self) -> None:
        super().__post_init__()
        # Validate all messages are correct type
        for msg in self.model_context:
            if not isinstance(msg, (SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage)):
                raise ValueError(f"Invalid message type in model_context: {type(msg)}")
