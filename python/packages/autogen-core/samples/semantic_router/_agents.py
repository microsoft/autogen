import asyncio
import logging

from _semantic_router_components import FinalResult, TerminationMessage, UserProxyMessage, WorkerAgentMessage
from autogen_core import DefaultTopicId, MessageContext, RoutedAgent, message_handler
from autogen_core.application.logging import TRACE_LOGGER_NAME

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(f"{TRACE_LOGGER_NAME}.workers")


class WorkerAgent(RoutedAgent):
    def __init__(self, name: str) -> None:
        super().__init__("A Worker Agent")
        self._name = name

    @message_handler
    async def my_message_handler(self, message: UserProxyMessage, ctx: MessageContext) -> None:
        assert ctx.topic_id is not None
        logger.debug(f"Received message from {message.source}: {message.content}")
        if "END" in message.content:
            await self.publish_message(
                TerminationMessage(reason="user terminated conversation", content=message.content, source=self.type),
                topic_id=DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
            )
        else:
            content = f"Hello from {self._name}! You said: {message.content}"
            logger.debug(f"Returning message: {content}")
            await self.publish_message(
                WorkerAgentMessage(content=content, source=ctx.topic_id.type),
                topic_id=DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
            )


class UserProxyAgent(RoutedAgent):
    """An agent that proxies user input from the console. Override the `get_user_input`
    method to customize how user input is retrieved.

    Args:
        description (str): The description of the agent.
    """

    def __init__(self, description: str) -> None:
        super().__init__(description)

    # When a conversation ends
    @message_handler
    async def on_terminate(self, message: TerminationMessage, ctx: MessageContext) -> None:
        assert ctx.topic_id is not None
        """Handle a publish now message. This method prompts the user for input, then publishes it."""
        logger.debug(f"Ending conversation with {ctx.sender} because {message.reason}")
        await self.publish_message(
            FinalResult(content=message.content, source=self.id.key),
            topic_id=DefaultTopicId(type="response", source=ctx.topic_id.source),
        )

    # When the agent responds back, user proxy adds it to history and then
    # sends to Closure Agent for API to respond
    @message_handler
    async def on_agent_message(self, message: WorkerAgentMessage, ctx: MessageContext) -> None:
        assert ctx.topic_id is not None
        logger.debug(f"Received message from {message.source}: {message.content}")
        logger.debug("Publishing message to Closure Agent")
        await self.publish_message(message, topic_id=DefaultTopicId(type="response", source=ctx.topic_id.source))

    async def get_user_input(self, prompt: str) -> str:
        """Get user input from the console. Override this method to customize how user input is retrieved."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)
