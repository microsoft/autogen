from typing import Callable, Optional

from autogen.experimental.chat import ChatOrchestrator
from autogen.experimental.chat_history import ChatHistoryReadOnly
from autogen.experimental.chat_histories.chat_history_list import ChatHistoryList
from autogen.experimental.types import AssistantMessage, MessageContext, SystemMessage

from ..agent import Agent, GenerateReplyResult

TransformInput = Callable[[ChatHistoryReadOnly], ChatHistoryReadOnly]


def default_transform_input(before_message: Optional[str], after_message: Optional[str]) -> TransformInput:

    def transform_input(messages: ChatHistoryReadOnly) -> ChatHistoryReadOnly:
        output = ChatHistoryList()
        if before_message is not None:
            output.append_message(SystemMessage(content=before_message), context=None)

        for m, c in zip(messages.messages, messages.contexts):
            output.append_message(m, context=c)

        if after_message is not None:
            output.append_message(SystemMessage(content=after_message), context=None)
        return output

    return transform_input


class ChatAgent(Agent):
    def __init__(
        self,
        name: str,
        chat: ChatOrchestrator,
        description: Optional[str] = None,
        input_transform: TransformInput = default_transform_input(None, None),
    ):
        self._chat = chat
        self._name = name
        self._description = description
        self._input_transform = input_transform

    @property
    def name(self) -> str:
        """The name of the agent."""
        return self._name

    @property
    def description(self) -> str:
        """The description of the agent. Used for the agent's introduction in
        a group chat setting."""
        return self._description or ""

    async def generate_reply(
        self,
        chat_history: ChatHistoryReadOnly,
    ) -> GenerateReplyResult:
        self._chat.reset()

        transformed_messages = self._input_transform(chat_history)

        for message, context in zip(transformed_messages.messages, transformed_messages.contexts):
            self._chat.append_message(message, context)

        while not self._chat.done:
            _ = await self._chat.step()

        return AssistantMessage(content=self._chat.result.summary), MessageContext(
            input=list(transformed_messages.messages), nested_chat_result=self._chat.result
        )
