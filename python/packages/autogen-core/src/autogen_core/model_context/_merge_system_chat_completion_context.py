from typing import List
from ..model_context import ChatCompletionContext
from ..models import LLMMessage, SystemMessage


class MergeSystemChatCompletionContext(ChatCompletionContext):
    """
    A `ChatCompletionContext` that merges multiple `SystemMessage`s into one.

    This is useful for models that **do not support multiple system prompts**,
    by collapsing all system messages into a single `SystemMessage` at the
    beginning of the conversation.

    Additionally, this context removes the `thought` field if present.

    Example:
        .. code-block:: python

            from autogen_core.model_context import MergeSystemChatCompletionContext
            from autogen_core.models import SystemMessage, UserMessage

            ctx = MergeSystemChatCompletionContext()
            await ctx.add_message(SystemMessage(content="System rule 1"))
            await ctx.add_message(SystemMessage(content="System rule 2"))
            await ctx.add_message(UserMessage(content="Hello!"))

            merged = await ctx.get_messages()
            # merged[0] => SystemMessage("System rule 1\nSystem rule 2")
    """

    async def get_messages(self) -> List[LLMMessage]:
        messages = self._messages
        merged_system_content = []
        messages_out: List[LLMMessage] = []

        for message in messages:
            if isinstance(message, SystemMessage):
                merged_system_content.append(message.content)
            else:
                messages_out.append(message)

        if merged_system_content:
            merged_system_message = SystemMessage(content="\n".join(merged_system_content))
            messages_out.insert(0, merged_system_message)

        return messages_out
