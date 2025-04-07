from typing_extensions import Annotated
from typing import List, Literal, Callable, Union
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
    content: str
    source: str
    type: Literal["TriggerMessage"] = "TriggerMessage"


BaseContextMessage = Union[UserMessage, AssistantMessage]
LLMMessageInstance = (SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage)

ContextMessage = Annotated[
    Union[LLMMessage, TriggerMessage], Field(discriminator="type")
]

SummarizngFunction = Callable[[List[LLMMessage], List[LLMMessage]], List[LLMMessage]]