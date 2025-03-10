import asyncio
import os
import sys
import time
from inspect import iscoroutinefunction
from typing import AsyncGenerator, Awaitable, Callable, Dict, List, Optional, TypeVar, Union, cast

from autogen_core import CancellationToken, Image
from autogen_core.models import RequestUsage
from colorama import Fore, Style, init

from autogen_agentchat.agents import UserProxyAgent
from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import (
    AgentEvent,
    ChatMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    UserInputRequestedEvent,
)


def _is_running_in_iterm() -> bool:
    return os.getenv("TERM_PROGRAM") == "iTerm.app"


def _is_output_a_tty() -> bool:
    return sys.stdout.isatty()


SyncInputFunc = Callable[[str], str]
AsyncInputFunc = Callable[[str, Optional[CancellationToken]], Awaitable[str]]
InputFuncType = Union[SyncInputFunc, AsyncInputFunc]

T = TypeVar("T", bound=TaskResult | Response)

# Initialize colorama
init(autoreset=True)


class UserInputManager:
    def __init__(self, callback: InputFuncType):
        self.input_events: Dict[str, asyncio.Event] = {}
        self.callback = callback

    def get_wrapped_callback(self) -> AsyncInputFunc:
        async def user_input_func_wrapper(prompt: str, cancellation_token: Optional[CancellationToken]) -> str:
            # Lookup the event for the prompt, if it exists wait for it.
            # If it doesn't exist, create it and store it.
            # Get request ID:
            request_id = UserProxyAgent.InputRequestContext.request_id()
            if request_id in self.input_events:
                event = self.input_events[request_id]
            else:
                event = asyncio.Event()
                self.input_events[request_id] = event

            await event.wait()

            del self.input_events[request_id]

            if iscoroutinefunction(self.callback):
                # Cast to AsyncInputFunc for proper typing
                async_func = cast(AsyncInputFunc, self.callback)
                return await async_func(prompt, cancellation_token)
            else:
                # Cast to SyncInputFunc for proper typing
                sync_func = cast(SyncInputFunc, self.callback)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, sync_func, prompt)

        return user_input_func_wrapper

    def notify_event_received(self, request_id: str) -> None:
        if request_id in self.input_events:
            self.input_events[request_id].set()
        else:
            event = asyncio.Event()
            self.input_events[request_id] = event


def aprint(
    output: str, end: str = "\n", flush: bool = False, color_map: Optional[Dict[str, str]] = None, source: str = ""
) -> Awaitable[None]:
    """
    Asynchronously print colored output based on the source.

    Args:
        source: The source identifier (e.g., "hypothesis", "search", etc.)
        output: The text to print
        end: The string appended after the output (default: newline)
        flush: Whether to force flush the output (default: False)
        color_map: A dictionary with {agent.name:Fore.}  to use to color the output (default: {})
    Returns:
        Awaitable for the print operation
    """
    # Determine the source identifier
    if isinstance(source, str):
        source_name = source.lower()
    else:
        # Try to get the class name if source is an object
        try:
            source_name = source.__class__.__name__.lower()
        except (AttributeError, TypeError):
            source_name = str(source).lower()

    if color_map:
        # Select appropriate color based on source
        color: str = Fore.WHITE  # Default color
        for role, role_color in color_map.items():
            if isinstance(role, str) and isinstance(role_color, str):
                if role in source_name:
                    color = role_color
                    break

        # Apply color to the output
        colored_output = f"{color}{output}{Style.RESET_ALL}"
    else:
        colored_output = output

    # Run print asynchronously
    return asyncio.to_thread(print, colored_output, end=end, flush=flush)


async def Console(
    stream: AsyncGenerator[AgentEvent | ChatMessage | T, None],
    *,
    no_inline_images: bool = False,
    output_stats: bool = False,
    user_input_manager: UserInputManager | None = None,
    colormap: Optional[Dict[str, str]] = None,
) -> T:
    """
    Consumes the message stream from :meth:`~autogen_agentchat.base.TaskRunner.run_stream`
    or :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream` and renders the messages to the console.
    Returns the last processed TaskResult or Response.

    Args:
        stream (AsyncGenerator[AgentEvent | ChatMessage | TaskResult, None] | AsyncGenerator[AgentEvent | ChatMessage | Response, None]): Message stream to render.
            This can be from :meth:`~autogen_agentchat.base.TaskRunner.run_stream` or :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream`.
        no_inline_images (bool, optional): If terminal is iTerm2 will render images inline. Use this to disable this behavior. Defaults to False.
        output_stats (bool, optional): (Experimental) If True, will output a summary of the messages and inline token usage info. Defaults to False.
        colormap: The color map for customizing the color of agent's messages in commandlines. Defaults to {}. The key is the agent's name, the value is the color at `colorama`. None if no using default colors in commandlines.
              e.g.,  color_map = {
                "critic": Fore.RED,
                "writer": Fore.GREEN,
                "reviewer": Fore.BLUE,
            }

    Returns:
        last_processed: A :class:`~autogen_agentchat.base.TaskResult` if the stream is from :meth:`~autogen_agentchat.base.TaskRunner.run_stream`
            or a :class:`~autogen_agentchat.base.Response` if the stream is from :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream`.
    """
    render_image_iterm = _is_running_in_iterm() and _is_output_a_tty() and not no_inline_images
    start_time = time.time()
    total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    last_processed: Optional[T] = None

    streaming_chunks: List[str] = []

    async for message in stream:
        if isinstance(message, TaskResult):
            duration = time.time() - start_time
            if output_stats:
                output = (
                    f"{'-' * 10} Summary {'-' * 10}\n"
                    f"Number of messages: {len(message.messages)}\n"
                    f"Finish reason: {message.stop_reason}\n"
                    f"Total prompt tokens: {total_usage.prompt_tokens}\n"
                    f"Total completion tokens: {total_usage.completion_tokens}\n"
                    f"Duration: {duration:.2f} seconds\n"
                )
                await aprint(output, end="", flush=True)

            # mypy ignore
            last_processed = message  # type: ignore

        elif isinstance(message, Response):
            duration = time.time() - start_time

            # Print final response.
            output = f"{'-' * 10} {message.chat_message.source} {'-' * 10}\n{_message_to_str(message.chat_message, render_image_iterm=render_image_iterm)}\n"
            if message.chat_message.models_usage:
                if output_stats:
                    output += f"[Prompt tokens: {message.chat_message.models_usage.prompt_tokens}, Completion tokens: {message.chat_message.models_usage.completion_tokens}]\n"
                total_usage.completion_tokens += message.chat_message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.chat_message.models_usage.prompt_tokens
            await aprint(output, end="", flush=True)

            # Print summary.
            if output_stats:
                if message.inner_messages is not None:
                    num_inner_messages = len(message.inner_messages)
                else:
                    num_inner_messages = 0
                output = (
                    f"{'-' * 10} Summary {'-' * 10}\n"
                    f"Number of inner messages: {num_inner_messages}\n"
                    f"Total prompt tokens: {total_usage.prompt_tokens}\n"
                    f"Total completion tokens: {total_usage.completion_tokens}\n"
                    f"Duration: {duration:.2f} seconds\n"
                )
                await aprint(output, end="", flush=True)

            # mypy ignore
            last_processed = message  # type: ignore
        # We don't want to print UserInputRequestedEvent messages, we just use them to signal the user input event.
        elif isinstance(message, UserInputRequestedEvent):
            if user_input_manager is not None:
                user_input_manager.notify_event_received(message.request_id)
        else:
            # Cast required for mypy to be happy
            message = cast(AgentEvent | ChatMessage, message)  # type: ignore
            if not streaming_chunks:
                # Print message sender.
                await aprint(
                    f"{'-' * 10} {message.source} {'-' * 10}",
                    end="\n",
                    flush=True,
                    color_map=colormap,
                    source=message.source,
                )
            if isinstance(message, ModelClientStreamingChunkEvent):
                await aprint(message.content, end="", color_map=colormap, source=message.source)
                streaming_chunks.append(message.content)
            else:
                if streaming_chunks:
                    streaming_chunks.clear()
                    # Chunked messages are already printed, so we just print a newline.
                    await aprint("", end="\n", flush=True, color_map=colormap, source=message.source)
                else:
                    # Print message content.
                    await aprint(
                        _message_to_str(message, render_image_iterm=render_image_iterm),
                        end="\n",
                        flush=True,
                        color_map=colormap,
                        source=message.source,
                    )
                if message.models_usage:
                    if output_stats:
                        await aprint(
                            f"[Prompt tokens: {message.models_usage.prompt_tokens}, Completion tokens: {message.models_usage.completion_tokens}]",
                            end="\n",
                            flush=True,
                            color_map=colormap,
                            source=message.source,
                        )
                    total_usage.completion_tokens += message.models_usage.completion_tokens
                    total_usage.prompt_tokens += message.models_usage.prompt_tokens

    if last_processed is None:
        raise ValueError("No TaskResult or Response was processed.")

    return last_processed


# iTerm2 image rendering protocol: https://iterm2.com/documentation-images.html
def _image_to_iterm(image: Image) -> str:
    image_data = image.to_base64()
    return f"\033]1337;File=inline=1:{image_data}\a\n"


def _message_to_str(message: AgentEvent | ChatMessage, *, render_image_iterm: bool = False) -> str:
    if isinstance(message, MultiModalMessage):
        result: List[str] = []
        for c in message.content:
            if isinstance(c, str):
                result.append(c)
            else:
                if render_image_iterm:
                    result.append(_image_to_iterm(c))
                else:
                    result.append("<image>")
        return "\n".join(result)
    else:
        return f"{message.content}"
