import asyncio

from ...components import TypeRoutedAgent, message_handler
from ...core import AgentRuntime, CancellationToken
from ..types import PublishNow, TextMessage


class UserProxyAgent(TypeRoutedAgent):
    def __init__(self, name: str, description: str, runtime: AgentRuntime, user_input_prompt: str) -> None:
        super().__init__(name, description, runtime)
        self._user_input_prompt = user_input_prompt

    @message_handler()
    async def on_publish_now(self, message: PublishNow, cancellation_token: CancellationToken) -> None:
        user_input = await self.get_user_input(self._user_input_prompt)
        await self._publish_message(TextMessage(content=user_input, source=self.name))

    async def get_user_input(self, prompt: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)
