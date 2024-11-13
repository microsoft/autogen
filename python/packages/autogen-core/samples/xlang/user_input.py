import asyncio
import logging
from typing import Union

from autogen_core.application.protos.agent_events_pb2 import ConversationClosed, Input, NewMessageReceived, Output
from autogen_core.base import MessageContext
from autogen_core.components import DefaultTopicId, RoutedAgent, default_subscription, message_handler
from autogen_core.components.models._types import SystemMessage

input_types = Union[ConversationClosed, Input, Output]

class UserProxy(RoutedAgent):
    """An agent that allows the user to play the role of an agent in the conversation via input."""

    DEFAULT_DESCRIPTION = "A human user."

    def __init__(
        self,
        description: str = DEFAULT_DESCRIPTION,
    ) -> None:
        super().__init__(description)

    @message_handler
    async def handle_user_chat_input(self, message: input_types, ctx: MessageContext) -> None:
        agnext_logger = logging.getLogger("autogen_core")

        if isinstance(message, Input):
            response = await self.ainput("User input ('exit' to quit): ")
            response = response.strip()
            agnext_logger.info(response)

            await self.publish_message(NewMessageReceived(message=response), topic_id=DefaultTopicId())
        elif isinstance(message, Output):
            agnext_logger.info(message.message)
        else:
            pass

    async def ainput(self, prompt: str) -> str:
        return await asyncio.to_thread(input, f"{prompt} ")
