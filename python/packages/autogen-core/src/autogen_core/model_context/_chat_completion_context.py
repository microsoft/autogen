from abc import ABC, abstractmethod
from typing import Any, List, Mapping

from pydantic import BaseModel, Field

from .._component_config import ComponentBase
from ..models import LLMMessage


class ChatCompletionContext(ABC, ComponentBase[BaseModel]):
    """An abstract base class for defining the interface of a chat completion context.
    A chat completion context lets agents store and retrieve LLM messages.
    It can be implemented with different recall strategies.

    Args:
        initial_messages (List[LLMMessage] | None): The initial messages.

    Example:

        To create a custom model context that filters out the thought field from AssistantMessage.
        This is useful for reasoning models like DeepSeek R1, which produces
        very long thought that is not needed for subsequent completions.

        .. code-block:: python

            from typing import List

            from autogen_core.model_context import UnboundedChatCompletionContext
            from autogen_core.models import AssistantMessage, LLMMessage


            class ReasoningModelContext(UnboundedChatCompletionContext):
                \"\"\"A model context for reasoning models.\"\"\"

                async def get_messages(self) -> List[LLMMessage]:
                    messages = await super().get_messages()
                    # Filter out thought field from AssistantMessage.
                    messages_out: List[LLMMessage] = []
                    for message in messages:
                        if isinstance(message, AssistantMessage):
                            message.thought = None
                        messages_out.append(message)
                    return messages_out

    """

    component_type = "chat_completion_context"

    def __init__(self, initial_messages: List[LLMMessage] | None = None) -> None:
        self._messages: List[LLMMessage] = []
        if initial_messages is not None:
            self._messages.extend(initial_messages)
        self._initial_messages = initial_messages

    async def add_message(self, message: LLMMessage) -> None:
        """Add a message to the context."""
        self._messages.append(message)

    @abstractmethod
    async def get_messages(self) -> List[LLMMessage]: ...

    async def clear(self) -> None:
        """Clear the context."""
        self._messages = []

    async def save_state(self) -> Mapping[str, Any]:
        return ChatCompletionContextState(messages=self._messages).model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        self._messages = ChatCompletionContextState.model_validate(state).messages


class ChatCompletionContextState(BaseModel):
    messages: List[LLMMessage] = Field(default_factory=list)
