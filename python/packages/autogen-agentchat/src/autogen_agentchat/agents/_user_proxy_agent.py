import asyncio
from inspect import iscoroutinefunction
from typing import Awaitable, Callable, List, Optional, Sequence, Union, cast

from autogen_core.base import CancellationToken

from ..base import Response
from ..messages import ChatMessage, TextMessage
from ._base_chat_agent import BaseChatAgent


class UserProxyAgent(BaseChatAgent):
    """An agent that can represent a human user in a chat.

    This agent serves as a proxy for human interaction, allowing for both synchronous
    and asynchronous input handling. It can be customized with different input
    functions to modify how user input is collected.
    """

    def __init__(
        self,
        name: str,
        description: str = "a human user",
        input_func: Optional[Callable[[str], Union[str, Awaitable[str]]]] = None,
    ) -> None:
        """Initialize the UserProxyAgent.

        Args:
            name: The name of the agent.
            description: A description of the agent's role, defaults to "a human user".
            input_func: Optional custom function for gathering user input. Can be either
                       synchronous or asynchronous. If None, uses built-in input() function.
        """
        super().__init__(name=name, description=description)
        self.input_func = input_func or input
        self._is_async = iscoroutinefunction(input_func) if input_func else False

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        return [TextMessage]

    async def _get_input(self, prompt: str) -> str:
        """Handle both synchronous and asynchronous input functions.

        This method abstracts away the differences between sync and async input
        functions, providing a consistent interface for getting user input.

        Args:
            prompt: The prompt to display to the user.

        Returns:
            The user's input as a string.
        """
        if self._is_async:
            result = await cast(Callable[[str], Awaitable[str]], self.input_func)(prompt)
            return result
        else:
            loop = asyncio.get_event_loop()
            sync_func = cast(Callable[[str], str], self.input_func)
            result = await loop.run_in_executor(None, sync_func, prompt)
            return result

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        """Handle incoming messages by requesting user input.

        This method is called when the agent receives messages and needs to respond.
        It prompts the user for input and returns their response.

        Args:
            messages: A sequence of incoming chat messages.
            cancellation_token: Token for cancelling the operation if needed.

        Returns:
            A Response object containing the user's input as a TextMessage.

        Raises:
            RuntimeError: If there is an error getting user input.
        """
        try:
            user_input = await self._get_input("Enter your response: ")
            return Response(chat_message=TextMessage(content=user_input, source=self.name))
        except Exception as e:
            raise RuntimeError(f"Failed to get user input: {str(e)}") from e

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass
