from typing import Awaitable, Callable, List

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


class GroupChatManager(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
        participant_topic_types: List[str],
        participant_descriptions: List[str],
        on_message_func: Callable[[str, str], Awaitable[None]],
        max_rounds: int = 3,
    ) -> None:
        super().__init__("Group chat manager")
        self._model_client = model_client
        self._num_rounds = 0
        self._participant_topic_types = participant_topic_types
        self._chat_history: List[GroupChatMessage] = []
        self._max_rounds = max_rounds
        self.console = Console()
        self._on_message_func = on_message_func
        self._participant_descriptions = participant_descriptions
        self._previous_participant_topic_type: str | None = None

    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        assert isinstance(message.body, UserMessage)
        await self._on_message_func(message.body.content, message.body.source)  # type: ignore[arg-type]
        self._chat_history.append(message.body)  # type: ignore[reportargumenttype,arg-type]

        # Format message history.
        messages: List[str] = []
        for msg in self._chat_history:
            if isinstance(msg.content, str):  # type: ignore[attr-defined]
                messages.append(f"{msg.source}: {msg.content}")  # type: ignore[attr-defined]
            elif isinstance(msg.content, list):  # type: ignore[attr-defined]
                messages.append(f"{msg.source}: {', '.join(msg.content)}")  # type: ignore[attr-defined,reportUnknownArgumentType]
        history = "\n".join(messages)
        # Format roles.
        roles = "\n".join(
            [
                f"{topic_type}: {description}".strip()
                for topic_type, description in zip(
                    self._participant_topic_types, self._participant_descriptions, strict=True
                )
                if topic_type != self._previous_participant_topic_type
            ]
        )
        participants = str(
            [
                topic_type
                for topic_type in self._participant_topic_types
                if topic_type != self._previous_participant_topic_type
            ]
        )

        selector_prompt = f"""You are in a role play game. The following roles are available:
{roles}.
Read the following conversation. Then select the next role from {participants} to play. Only return the role.

{history}

Read the above conversation. Then select the next role from {participants} to play. if you think it's enough talking (for example they have talked for {self._max_rounds} rounds), return 'FINISH'.
"""
        system_message = SystemMessage(selector_prompt)
        completion = await self._model_client.create([system_message], cancellation_token=ctx.cancellation_token)
        assert isinstance(completion.content, str)

        if completion.content.upper() == "FINISH":
            manager_message = f"\n{'-'*80}\n Manager ({id(self)}): I think it's enough iterations on the story! Thanks for collaborating!"
            await self._on_message_func(manager_message, "group_chat_manager")
            self.console.print(Markdown(manager_message))
            return

        selected_topic_type: str
        for topic_type in self._participant_topic_types:
            if topic_type.lower() in completion.content.lower():
                selected_topic_type = topic_type
                self._previous_participant_topic_type = selected_topic_type
                self.console.print(
                    Markdown(f"\n{'-'*80}\n Manager ({id(self)}): Asking `{selected_topic_type}` to speak")
                )
                await self.publish_message(RequestToSpeak(), DefaultTopicId(type=selected_topic_type))
                return
        raise ValueError(f"Invalid role selected: {completion.content}")
