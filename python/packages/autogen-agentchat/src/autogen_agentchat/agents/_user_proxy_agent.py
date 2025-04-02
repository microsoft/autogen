import asyncio
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from inspect import iscoroutinefunction
from typing import Any, AsyncGenerator, Awaitable, Callable, ClassVar, Generator, Optional, Sequence, Union, cast

from autogen_core import CancellationToken, Component
from pydantic import BaseModel
from typing_extensions import Self

from ..base import Response
from ..messages import BaseAgentEvent, BaseChatMessage, HandoffMessage, TextMessage, UserInputRequestedEvent
from ._base_chat_agent import BaseChatAgent

SyncInputFunc = Callable[[str], str]
AsyncInputFunc = Callable[[str, Optional[CancellationToken]], Awaitable[str]]
InputFuncType = Union[SyncInputFunc, AsyncInputFunc]


# TODO: check if using to_thread fixes this in jupyter
async def cancellable_input(prompt: str, cancellation_token: Optional[CancellationToken]) -> str:
    task: asyncio.Task[str] = asyncio.create_task(asyncio.to_thread(input, prompt))
    if cancellation_token is not None:
        cancellation_token.link_future(task)
    return await task


class UserProxyAgentConfig(BaseModel):
    """Declarative configuration for the UserProxyAgent."""

    name: str
    description: str = "A human user"
    input_func: str | None = None


class UserProxyAgent(BaseChatAgent, Component[UserProxyAgentConfig]):
    """An agent that can represent a human user through an input function.

    This agent can be used to represent a human user in a chat system by providing a custom input function.

    .. note::

        Using :class:`UserProxyAgent` puts a running team in a temporary blocked
        state until the user responds. So it is important to time out the user input
        function and cancel using the :class:`~autogen_core.CancellationToken` if the user does not respond.
        The input function should also handle exceptions and return a default response if needed.

        For typical use cases that involve
        slow human responses, it is recommended to use termination conditions
        such as :class:`~autogen_agentchat.conditions.HandoffTermination` or :class:`~autogen_agentchat.conditions.SourceMatchTermination`
        to stop the running team and return the control to the application.
        You can run the team again with the user input. This way, the state of the team
        can be saved and restored when the user responds.

        See `Human-in-the-loop <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html>`_ for more information.

    Args:
        name (str): The name of the agent.
        description (str, optional): A description of the agent.
        input_func (Optional[Callable[[str], str]], Callable[[str, Optional[CancellationToken]], Awaitable[str]]): A function that takes a prompt and returns a user input string.

    For examples of integrating with web and UI frameworks, see the following:

    * `FastAPI <https://github.com/microsoft/autogen/tree/main/python/samples/agentchat_fastapi>`_
    * `ChainLit <https://github.com/microsoft/autogen/tree/main/python/samples/agentchat_chainlit>`_

    Example:
        Simple usage case::

            import asyncio
            from autogen_core import CancellationToken
            from autogen_agentchat.agents import UserProxyAgent
            from autogen_agentchat.messages import TextMessage


            async def simple_user_agent():
                agent = UserProxyAgent("user_proxy")
                response = await asyncio.create_task(
                    agent.on_messages(
                        [TextMessage(content="What is your name? ", source="user")],
                        cancellation_token=CancellationToken(),
                    )
                )
                assert isinstance(response.chat_message, TextMessage)
                print(f"Your name is {response.chat_message.content}")

    Example:
        Cancellable usage case::

            import asyncio
            from typing import Any
            from autogen_core import CancellationToken
            from autogen_agentchat.agents import UserProxyAgent
            from autogen_agentchat.messages import TextMessage


            token = CancellationToken()
            agent = UserProxyAgent("user_proxy")


            async def timeout(delay: float):
                await asyncio.sleep(delay)


            def cancellation_callback(task: asyncio.Task[Any]):
                token.cancel()


            async def cancellable_user_agent():
                try:
                    timeout_task = asyncio.create_task(timeout(3))
                    timeout_task.add_done_callback(cancellation_callback)
                    agent_task = asyncio.create_task(
                        agent.on_messages(
                            [TextMessage(content="What is your name? ", source="user")],
                            cancellation_token=token,
                        )
                    )
                    response = await agent_task
                    assert isinstance(response.chat_message, TextMessage)
                    print(f"Your name is {response.chat_message.content}")
                except Exception as e:
                    print(f"Exception: {e}")
                except BaseException as e:
                    print(f"BaseException: {e}")
    """

    component_type = "agent"
    component_provider_override = "autogen_agentchat.agents.UserProxyAgent"
    component_config_schema = UserProxyAgentConfig

    class InputRequestContext:
        def __init__(self) -> None:
            raise RuntimeError(
                "InputRequestContext cannot be instantiated. It is a static class that provides context management for user input requests."
            )

        _INPUT_REQUEST_CONTEXT_VAR: ClassVar[ContextVar[str]] = ContextVar("_INPUT_REQUEST_CONTEXT_VAR")

        @classmethod
        @contextmanager
        def populate_context(cls, ctx: str) -> Generator[None, Any, None]:
            """:meta private:"""
            token = UserProxyAgent.InputRequestContext._INPUT_REQUEST_CONTEXT_VAR.set(ctx)
            try:
                yield
            finally:
                UserProxyAgent.InputRequestContext._INPUT_REQUEST_CONTEXT_VAR.reset(token)

        @classmethod
        def request_id(cls) -> str:
            try:
                return cls._INPUT_REQUEST_CONTEXT_VAR.get()
            except LookupError as e:
                raise RuntimeError(
                    "InputRequestContext.runtime() must be called within the input callback of a UserProxyAgent."
                ) from e

    def __init__(
        self,
        name: str,
        *,
        description: str = "A human user",
        input_func: Optional[InputFuncType] = None,
    ) -> None:
        """Initialize the UserProxyAgent."""
        super().__init__(name=name, description=description)
        self.input_func = input_func or cancellable_input
        self._is_async = iscoroutinefunction(self.input_func)

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        """Message types this agent can produce."""
        return (TextMessage, HandoffMessage)

    def _get_latest_handoff(self, messages: Sequence[BaseChatMessage]) -> Optional[HandoffMessage]:
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

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

    async def on_messages_stream(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        """Handle incoming messages by requesting user input."""
        try:
            # Check for handoff first
            handoff = self._get_latest_handoff(messages)
            prompt = (
                f"Handoff received from {handoff.source}. Enter your response: " if handoff else "Enter your response: "
            )

            request_id = str(uuid.uuid4())

            input_requested_event = UserInputRequestedEvent(request_id=request_id, source=self.name)
            yield input_requested_event
            with UserProxyAgent.InputRequestContext.populate_context(request_id):
                user_input = await self._get_input(prompt, cancellation_token)

            # Return appropriate message type based on handoff presence
            if handoff:
                yield Response(chat_message=HandoffMessage(content=user_input, target=handoff.source, source=self.name))
            else:
                yield Response(chat_message=TextMessage(content=user_input, source=self.name))

        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to get user input: {str(e)}") from e

    async def on_reset(self, cancellation_token: Optional[CancellationToken] = None) -> None:
        """Reset agent state."""
        pass

    def _to_config(self) -> UserProxyAgentConfig:
        # TODO: Add ability to serialie input_func
        return UserProxyAgentConfig(name=self.name, description=self.description, input_func=None)

    @classmethod
    def _from_config(cls, config: UserProxyAgentConfig) -> Self:
        return cls(name=config.name, description=config.description, input_func=None)
