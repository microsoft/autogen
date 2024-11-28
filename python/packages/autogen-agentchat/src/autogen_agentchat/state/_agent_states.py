from dataclasses import dataclass, field
from typing import List
from autogen_core.components.models import SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage, LLMMessage
from ._base import BaseState


@dataclass
class AssistantAgentState(BaseState):
    state_type: str = "AssistantAgentState"
    model_context: List[LLMMessage] = field(default_factory=list)
    version: str = "1.0.0"

    def __post_init__(self):
        super().__post_init__()
        # Validate all messages are correct type
        for msg in self.model_context:
            if not isinstance(msg, (SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage)):
                raise ValueError(
                    f"Invalid message type in model_context: {type(msg)}")
