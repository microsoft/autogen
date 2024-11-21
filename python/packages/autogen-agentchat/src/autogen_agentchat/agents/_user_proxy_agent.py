import asyncio
from inspect import iscoroutinefunction
from typing import Awaitable, Callable, List, Optional, Sequence, Union, cast

from autogen_core.base import CancellationToken

from ..base import Response
from ..messages import ChatMessage, HandoffMessage, TextMessage
from ._base_chat_agent import BaseChatAgent

# Define input function types more precisely
SyncInputFunc = Callable[[str], str]
AsyncInputFunc = Callable[[str, Optional[CancellationToken]], Awaitable[str]]
InputFuncType = Union[SyncInputFunc, AsyncInputFunc]


class UserProxyAgent(BaseChatAgent):
    """An agent that can represent a human user in a chat."""

    def __init__(
        self,
        name: str,
        description: str = "a human user",
        input_func: Optional[InputFuncType] = None,
    ) -> None:
        """Initialize the UserProxyAgent."""
        super().__init__(name=name, description=description)
        self.input_func = input_func or input
        self._is_async = iscoroutinefunction(self.input_func)

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        """Message types this agent can produce."""
        return [TextMessage, HandoffMessage]

    def _get_latest_handoff(self, messages: Sequence[ChatMessage]) -> Optional[HandoffMessage]:
        """Find the most recent HandoffMessage in the message sequence."""
        for message in reversed(messages):
            if isinstance(message, HandoffMessage):
                return message
        return None

    async def _get_input(self, prompt: str, cancellation_token: Optional[CancellationToken]) -> str:
        """Handle input based on function signature."""
        try:
            if self._is_async:
                # Cast to AsyncInputFunc for proper typing
                async_func = cast(AsyncInputFunc, self.input_func)
                return await async_func(prompt, cancellation_token)
            else:
                # Cast to SyncInputFunc for proper typing
                sync_func = cast(SyncInputFunc, self.input_func)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, sync_func, prompt)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to get user input: {str(e)}") from e

    async def on_messages(
        self, messages: Sequence[ChatMessage], cancellation_token: Optional[CancellationToken] = None
    ) -> Response:
        """Handle incoming messages by requesting user input."""
        try:
            # Check for handoff first
            handoff = self._get_latest_handoff(messages)
            prompt = (
                f"Handoff received from {handoff.source}. Enter your response: " if handoff else "Enter your response: "
            )

            user_input = await self._get_input(prompt, cancellation_token)

            # Return appropriate message type based on handoff presence
            if handoff:
                return Response(
                    chat_message=HandoffMessage(content=user_input, target=handoff.source, source=self.name)
                )
            else:
                return Response(chat_message=TextMessage(content=user_input, source=self.name))

        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to get user input: {str(e)}") from e

    async def on_reset(self, cancellation_token: Optional[CancellationToken] = None) -> None:
        """Reset agent state."""
        pass
