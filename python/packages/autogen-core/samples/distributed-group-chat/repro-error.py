from autogen_core.base import MessageContext
from autogen_core.components import message_handler, RoutedAgent
from dataclasses import dataclass


@dataclass
class MessageType: ...


class BaseTestAgent(RoutedAgent):
    @message_handler
    async def handle_message(self, message: MessageType, ctx: MessageContext) -> None:
        pass


class TestAgent(BaseTestAgent):
    @message_handler
    async def handle_message(self, message: MessageType, ctx: MessageContext) -> None:
        pass
