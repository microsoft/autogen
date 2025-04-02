from typing import List
from autogen_core.model_context import UnboundedChatCompletionContext
from autogen_core.models import AssistantMessage, LLMMessage


class ReasoningModelContext(UnboundedChatCompletionContext):
    """A model context for reasoning models."""

    async def get_messages(self) -> List[LLMMessage]:
        messages = await super().get_messages()
        # Filter out thought field from AssistantMessage.
        messages_out = []
        for message in messages:
            if isinstance(message, AssistantMessage):
                message.thought = None
            messages_out.append(message)
        return messages_out