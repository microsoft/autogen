import asyncio
from typing import List

from _types import GroupChatMessage, RequestToSpeak
from autogen_core.base import MessageContext
from autogen_core.components import DefaultTopicId, RoutedAgent, message_handler
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from rich.console import Console
from rich.markdown import Markdown


class BaseGroupChatAgent(RoutedAgent):
    """A group chat participant using an LLM."""

    def __init__(
        self,
        description: str,
        group_chat_topic_type: str,
        model_client: ChatCompletionClient,
        system_message: str,
    ) -> None:
        super().__init__(description=description)
        self._group_chat_topic_type = group_chat_topic_type
        self._model_client = model_client
        self._system_message = SystemMessage(system_message)
        self._chat_history: List[LLMMessage] = []

    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        self._chat_history.extend(
            [
                UserMessage(content=f"Transferred to {message.body.source}", source="system"),  # type: ignore[union-attr]
                message.body,
            ]
        )

    @message_handler
    async def handle_request_to_speak(self, message: RequestToSpeak, ctx: MessageContext) -> None:
        self._chat_history.append(
            UserMessage(content=f"Transferred to {self.id.type}, adopt the persona immediately.", source="system")
        )
        completion = await self._model_client.create([self._system_message] + self._chat_history)
        assert isinstance(completion.content, str)
        self._chat_history.append(AssistantMessage(content=completion.content, source=self.id.type))
        Console().print(Markdown(f"**{self.id.type}**: {completion.content}\n"))

        await self.publish_message(
            GroupChatMessage(body=UserMessage(content=completion.content, source=self.id.type)),
            topic_id=DefaultTopicId(type=self._group_chat_topic_type),
        )


class RoundRobingGroupChatManager(RoutedAgent):
    def __init__(self, participant_topic_types: List[str], max_rounds: int = 3) -> None:
        super().__init__("Group chat manager")
        self._num_rounds = 0
        self._participant_topic_types = participant_topic_types
        self._chat_history: List[GroupChatMessage] = []
        self._max_rounds = max_rounds
        self.console = Console()

    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        self._chat_history.append(message)
        assert isinstance(message.body, UserMessage)
        if self._num_rounds >= self._max_rounds:
            self.console.print(Markdown(f"\n ---> Finished running `{self._num_rounds}` rounds! <---"))
            await asyncio.sleep(1)
            return
        speaker_topic_type = self._participant_topic_types[self._num_rounds % len(self._participant_topic_types)]
        self._num_rounds += 1
        self.console.print(Markdown(f"\n{'-'*80}\n Manager ({id(self)}): Asking `{speaker_topic_type}` to speak"))
        await asyncio.sleep(1)
        await self.publish_message(RequestToSpeak(), DefaultTopicId(type=speaker_topic_type))
