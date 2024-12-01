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
    """An agent that can represent a human user through an input function.

    This agent can be used to represent a human user in a chat system by providing a custom input function.

    Args:
        name (str): The name of the agent.
        description (str, optional): A description of the agent.
        input_func (Optional[Callable[[str], str]], Callable[[str, Optional[CancellationToken]], Awaitable[str]]): A function that takes a prompt and returns a user input string.

    .. note::

        Using :class:`UserProxyAgent` puts a running team in a temporary blocked
        state until the user responds. So it is important to time out the user input
        function and cancel using the :class:`~autogen_core.base.CancellationToken` if the user does not respond.
        The input function should also handle exceptions and return a default response if needed.

        For typical use cases that involve
        slow human responses, it is recommended to use termination conditions
        such as :class:`~autogen_agentchat.task.HandoffTermination` or :class:`~autogen_agentchat.task.SourceMatchTermination`
        to stop the running team and return the control to the application.
        You can run the team again with the user input. This way, the state of the team
        can be saved and restored when the user responds.

        See `Pause for User Input <https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/teams.html#pause-for-user-input>`_ for more information.

    """

    def __init__(
        self,
        name: str,
        *,
        description: str = "A human user",
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
        """Find the HandoffMessage in the message sequence that addresses this agent."""
        if len(messages) > 0 and isinstance(messages[-1], HandoffMessage):
            if messages[-1].target == self.name:
                return messages[-1]
            else:
                raise RuntimeError(f"Handoff message target does not match agent name: {messages[-1].source}")
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
