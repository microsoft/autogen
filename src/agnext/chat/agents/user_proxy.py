import asyncio

from ...components import TypeRoutedAgent, message_handler
from ...core import AgentRuntime, CancellationToken
from ..types import PublishNow, TextMessage


class UserProxyAgent(TypeRoutedAgent):
    """An agent that proxies user input from the console. Override the `get_user_input`
    method to customize how user input is retrieved.

    Args:
        name (str): The name of the agent.
        description (str): The description of the agent.
        runtime (AgentRuntime): The runtime to register the agent.
        user_input_prompt (str): The console prompt to show to the user when asking for input.
    """

    def __init__(self, name: str, description: str, runtime: AgentRuntime, user_input_prompt: str) -> None:
        super().__init__(name, description, runtime)
        self._user_input_prompt = user_input_prompt

    @message_handler()
    async def on_publish_now(self, message: PublishNow, cancellation_token: CancellationToken) -> None:
        """Handle a publish now message. This method prompts the user for input, then publishes it."""
        user_input = await self.get_user_input(self._user_input_prompt)
        await self._publish_message(TextMessage(content=user_input, source=self.metadata["name"]))

    async def get_user_input(self, prompt: str) -> str:
        """Get user input from the console. Override this method to customize how user input is retrieved."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)
