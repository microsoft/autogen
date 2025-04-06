from typing_extensions import Annotated
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field

from ...models import LLMMessage, UserMessage, AssistantMessage

class TriggerMessage(BaseModel):
    """A message requesting trigger of a completion context."""
    type: Literal["TriggerMessage"] = "TriggerMessage"
    content: str
    source: str

    def __init__(self, content: str, source: str) -> None:
        self.content = content
        self.source = source


BaseContextMessage = Union[UserMessage, AssistantMessage]

ContextMessage = Annotated[
    Union[LLMMessage, TriggerMessage], Field(discriminator="type")
]
