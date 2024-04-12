from typing import Callable, List, Optional

from autogen.experimental.chat import ChatOrchestrator
from autogen.experimental.types import AssistantMessage, MessageAndSender, MessageContext, SystemMessage

from ..agent import Agent, GenerateReplyResult

TransformInput = Callable[[List[MessageAndSender]], List[MessageAndSender]]


def default_transform_input(before_message: Optional[str], after_message: Optional[str]) -> TransformInput:
    def transform_input(messages: List[MessageAndSender]) -> List[MessageAndSender]:
        if before_message is not None:
            messages.insert(0, MessageAndSender(SystemMessage(content=before_message)))
        if after_message is not None:
            messages.append(MessageAndSender(SystemMessage(content=after_message)))
        return messages

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
        messages: List[MessageAndSender],
    ) -> GenerateReplyResult:
        self._chat.reset()

        messages = self._input_transform(messages.copy())

        for message in messages:
            self._chat.append_message(message)

        while not self._chat.done:
            _ = await self._chat.step()

        return AssistantMessage(content=self._chat.result.summary), MessageContext(
            input=[x.message for x in messages], nested_chat_result=self._chat.result
        )
