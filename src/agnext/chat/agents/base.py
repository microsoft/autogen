from ...agent_components.type_routed_agent import TypeRoutedAgent, message_handler
from ...core.cancellation_token import CancellationToken
from ..messages import ChatMessage
from ..runtimes import SingleThreadedRuntime


class BaseChatAgent(TypeRoutedAgent[ChatMessage]):
    """The BaseAgent class for the chat API."""

    def __init__(self, name: str, description: str, runtime: SingleThreadedRuntime) -> None:
        super().__init__(name, runtime)
        self._description = description

    @property
    def description(self) -> str:
        """The description of the agent."""
        return self._description

    async def on_chat_message(self, message: ChatMessage) -> ChatMessage:
        """The method to handle chat messages."""
        raise NotImplementedError

    # TODO: how should we expose cancellation in chat layer?
    @message_handler(ChatMessage)
    async def on_chat_message_with_cancellation(
        self, message: ChatMessage, cancellation_token: CancellationToken
    ) -> ChatMessage:
        """The method to handle chat messages with cancellation."""
        return await self.on_chat_message(message)
