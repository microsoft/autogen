import asyncio

from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import MessageContext

from ..types import PublishNow, TextMessage


class UserProxyAgent(TypeRoutedAgent):
    """An agent that proxies user input from the console. Override the `get_user_input`
    method to customize how user input is retrieved.

    Args:
        description (str): The description of the agent.
        user_input_prompt (str): The console prompt to show to the user when asking for input.
    """

    def __init__(self, description: str, user_input_prompt: str) -> None:
        super().__init__(description)
        self._user_input_prompt = user_input_prompt

    @message_handler()
    async def on_publish_now(self, message: PublishNow, ctx: MessageContext) -> None:
        """Handle a publish now message. This method prompts the user for input, then publishes it."""
        user_input = await self.get_user_input(self._user_input_prompt)
        assert ctx.topic_id is not None
        await self.publish_message(TextMessage(content=user_input, source=self.metadata["type"]), topic_id=ctx.topic_id)

    async def get_user_input(self, prompt: str) -> str:
        """Get user input from the console. Override this method to customize how user input is retrieved."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)
