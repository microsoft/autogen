from typing import Callable, List, Optional, Sequence, Union, Awaitable
from inspect import iscoroutinefunction
from ._base_chat_agent import BaseChatAgent
from ..base import Response
from ..messages import ChatMessage, TextMessage
from autogen_core.base import CancellationToken
import asyncio


class UserProxyAgent(BaseChatAgent):
    """An agent that can represent a human user in a chat."""

    def __init__(
        self,
        name: str,
        description: str = "a human user",
        input_func: Optional[Callable[..., Union[str, Awaitable[str]]]] = None,
    ) -> None:
        super().__init__(name=name, description=description)
        self.input_func = input_func or input
        self._is_async = iscoroutinefunction(
            input_func) if input_func else False

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        return [TextMessage]

    async def _get_input(self, prompt: str) -> str:
        """Handle both sync and async input functions"""
        if self._is_async:
            result = await self.input_func(prompt)  # type: ignore
            return str(result)
        else:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda p: self.input_func(p),  # type: ignore
                prompt
            )
            return str(result)

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        try:
            user_input = await self._get_input("Enter your response: ")
            return Response(chat_message=TextMessage(content=user_input, source=self.name))
        except Exception as e:
            raise RuntimeError(f"Failed to get user input: {str(e)}") from e

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass
