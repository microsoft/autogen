from typing import List, Optional

from autogen.experimental.chat import ChatOrchestrator
from autogen.experimental.types import AssistantMessage, MessageAndSender, MessageContext

from ..agent import Agent, GenerateReplyResult


class ChatAgent(Agent):
    def __init__(
        self, name: str, chat: ChatOrchestrator, description: Optional[str] = None, intitial_message: str = ""
    ):
        self._chat = chat
        self._name = name
        self._description = description
        self._initial_message = intitial_message

    @property
    def name(self) -> str:
        """The name of the agent."""
        raise NotImplementedError

    @property
    def description(self) -> str:
        """The description of the agent. Used for the agent's introduction in
        a group chat setting."""
        raise NotImplementedError

    def reset(self) -> None:
        """Reset the agent's state."""
        raise NotImplementedError

    async def generate_reply(
        self,
        messages: List[MessageAndSender],
    ) -> GenerateReplyResult:
        # self._chat.reset()

        for message in messages:
            self._chat.append_message(message)

        while not self._chat.done:
            _ = await self._chat.step()

        return AssistantMessage(content=self._chat.result.summary), MessageContext(nested_chat_result=self._chat.result)
