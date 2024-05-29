from typing import Any, Callable, Dict, List, Mapping

from agnext.agent_components.model_client import ModelClient
from agnext.agent_components.type_routed_agent import TypeRoutedAgent, message_handler
from agnext.agent_components.types import SystemMessage
from agnext.chat.agents.base import BaseChatAgent
from agnext.chat.types import Message, Reset, RespondNow, ResponseFormat, TextMessage
from agnext.chat.utils import convert_messages_to_llm_messages
from agnext.core import AgentRuntime, CancellationToken


class ChatCompletionAgent(BaseChatAgent, TypeRoutedAgent):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,
        system_messages: List[SystemMessage],
        model_client: ModelClient,
        tools: Dict[str, Callable[..., str]] | None = None,
    ) -> None:
        super().__init__(name, description, runtime)
        self._system_messages = system_messages
        self._client = model_client
        self._tools = tools or {}
        self._chat_messages: List[Message] = []

    @message_handler(TextMessage)
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:
        # Add a user message.
        self._chat_messages.append(message)

    @message_handler(Reset)
    async def on_reset(self, message: Reset, cancellation_token: CancellationToken) -> None:
        # Reset the chat messages.
        self._chat_messages = []

    @message_handler(RespondNow)
    async def on_respond_now(self, message: RespondNow, cancellation_token: CancellationToken) -> TextMessage:
        if message.response_format == ResponseFormat.json_object:
            response_format = {"type": "json_object"}
        else:
            response_format = {"type": "text"}
        response = await self._client.create(
            self._system_messages + convert_messages_to_llm_messages(self._chat_messages, self.name),
            extra_create_args={"response_format": response_format},
        )
        if isinstance(response.content, str):
            return TextMessage(content=response.content, source=self.name)
        else:
            raise ValueError(f"Unexpected response: {response.content}")

    def save_state(self) -> Mapping[str, Any]:
        return {
            "description": self.description,
            "chat_messages": self._chat_messages,
            "system_messages": self._system_messages,
        }

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._chat_messages = state["chat_messages"]
        self._system_messages = state["system_messages"]
        self._description = state["description"]
