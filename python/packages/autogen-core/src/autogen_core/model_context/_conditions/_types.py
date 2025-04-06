from typing_extensions import Annotated
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field

from ...models import (
    LLMMessage,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    FunctionExecutionResultMessage,
)

class TriggerMessage(BaseModel):
    """A message requesting trigger of a completion context."""
    type: Literal["TriggerMessage"] = "TriggerMessage"
    content: str
    source: str

    def __init__(self, content: str, source: str) -> None:
        self.content = content
        self.source = source


BaseContextMessage = Union[UserMessage, AssistantMessage]
LLMMessageInstance = (SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage)

ContextMessage = Annotated[
    Union[LLMMessage, TriggerMessage], Field(discriminator="type")
]
