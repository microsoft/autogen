"""Input function protocols for various input types."""

from typing import Protocol, Literal, Optional, cast
from autogen_core import CancellationToken

from inspect import iscoroutinefunction
from autogen_agentchat.agents._user_proxy_agent import InputFuncType as AGInputFuncType

# This module provides input function protocols that extend the basic AgentChat
# input function types to support different types of input requests.

InputRequestType = Literal["text_input", "approval"]


class SyncInputFunc(Protocol):
    """Protocol for synchronous input function."""

    def __call__(self, prompt: str, input_type: InputRequestType = "text_input") -> str:
        """Call the input function with a prompt and optional cancellation token."""
        ...


class AsyncInputFunc(Protocol):
    """Protocol for asynchronous input function."""

    async def __call__(
        self,
        prompt: str,
        cancellation_token: Optional[CancellationToken],
        input_type: InputRequestType = "text_input",
    ) -> str:
        """Call the input function with a prompt and optional cancellation token."""
        ...


InputFuncType = SyncInputFunc | AsyncInputFunc


def make_agentchat_input_func(
    input_func: Optional[InputFuncType] = None,
) -> Optional[AGInputFuncType]:
    """Convert a custom input function to the AgentChat input function format."""
    if input_func is None:
        return None

    if iscoroutinefunction(input_func):
        actual_input_func = cast(AsyncInputFunc, input_func)

        async def async_input_func(
            prompt: str, cancellation_token: Optional[CancellationToken]
        ) -> str:
            return await actual_input_func(
                prompt, cancellation_token, input_type="text_input"
            )

        return async_input_func
    else:
        actual_input_func = cast(SyncInputFunc, input_func)

        def sync_input_func(prompt: str) -> str:
            return actual_input_func(prompt, input_type="text_input")

        return sync_input_func