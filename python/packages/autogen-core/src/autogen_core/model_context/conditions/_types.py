from typing import Callable, List, Literal, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from ...models import (
    AssistantMessage,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)


class TriggerMessage(BaseModel):
    """A message requesting trigger of a completion context."""

    content: str
    source: str
    type: Literal["TriggerMessage"] = "TriggerMessage"


BaseContextMessage = Union[UserMessage, AssistantMessage]
BaseContextMessageTypes = (UserMessage, AssistantMessage)

LLMMessageInstance = (SystemMessage, UserMessage, AssistantMessage, FunctionExecutionResultMessage)

ContextMessage = Annotated[Union[LLMMessage, TriggerMessage], Field(discriminator="type")]

SummarizngFunction = Callable[[List[LLMMessage], List[LLMMessage]], List[LLMMessage]]
