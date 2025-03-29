import asyncio
import os
import sys
import time
from typing import (
    AsyncGenerator,
    Awaitable,
    List,
    Optional,
    Tuple,
    TypeVar,
    cast,
)

from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    UserInputRequestedEvent,
)
from autogen_agentchat.ui._console import UserInputManager
from autogen_core import Image
from autogen_core.models import RequestUsage
from rich.align import AlignMethod
from rich.console import Console
from rich.panel import Panel

AGENT_COLORS = {
    "user": "bright_green",
    "MagenticOneOrchestrator": "bright_blue",
    "WebSurfer": "bright_yellow",
    "FileSurfer": "bright_cyan",
    "Coder": "bright_magenta",
    "Executor": "bright_red",
}
DEFAULT_AGENT_COLOR = "white"

AGENT_ALIGNMENTS: dict[str, AlignMethod] = {"user": "right", "MagenticOneOrchestrator": "center"}
DEFAULT_AGENT_ALIGNMENT: AlignMethod = "left"


def _is_running_in_iterm() -> bool:
    return os.getenv("TERM_PROGRAM") == "iTerm.app"


def _is_output_a_tty() -> bool:
    return sys.stdout.isatty()


T = TypeVar("T", bound=TaskResult | Response)


def aprint(output: str, end: str = "\n") -> Awaitable[None]:
    return asyncio.to_thread(print, output, end=end)


def _extract_message_content(message: BaseAgentEvent | BaseChatMessage) -> Tuple[List[str], List[Image]]:
    if isinstance(message, MultiModalMessage):
        text_parts = [item for item in message.content if isinstance(item, str)]
        image_parts = [item for item in message.content if isinstance(item, Image)]
    else:
        text_parts = [message.to_text()]
        image_parts = []
    return text_parts, image_parts


async def _aprint_panel(console: Console, text: str, title: str) -> None:
    color = AGENT_COLORS.get(title, DEFAULT_AGENT_COLOR)
    title_align = AGENT_ALIGNMENTS.get(title, DEFAULT_AGENT_ALIGNMENT)

    await asyncio.to_thread(
        console.print,
        Panel(
            text,
            title=title,
            title_align=title_align,
            border_style=color,
        ),
    )


async def _aprint_message_content(
    console: Console,
    text_parts: List[str],
    image_parts: List[Image],
    source: str,
    *,
    render_image_iterm: bool = False,
) -> None:
    if text_parts:
        await _aprint_panel(console, "\n".join(text_parts), source)

    for img in image_parts:
        if render_image_iterm:
            await aprint(_image_to_iterm(img))
        else:
            await aprint("<image>\n")


async def RichConsole(
    stream: AsyncGenerator[BaseAgentEvent | BaseChatMessage | T, None],
    *,
    no_inline_images: bool = False,
    output_stats: bool = False,
    user_input_manager: UserInputManager | None = None,
) -> T:
    """
    Consumes the message stream from :meth:`~autogen_agentchat.base.TaskRunner.run_stream`
    or :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream` and renders the messages to the console.
    Returns the last processed TaskResult or Response.

    .. note::

        `output_stats` is experimental and the stats may not be accurate.
        It will be improved in future releases.

    Args:
        stream (AsyncGenerator[AgentEvent | ChatMessage | TaskResult, None] | AsyncGenerator[AgentEvent | ChatMessage | Response, None]): Message stream to render.
            This can be from :meth:`~autogen_agentchat.base.TaskRunner.run_stream` or :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream`.
        no_inline_images (bool, optional): If terminal is iTerm2 will render images inline. Use this to disable this behavior. Defaults to False.
        output_stats (bool, optional): (Experimental) If True, will output a summary of the messages and inline token usage info. Defaults to False.

    Returns:
        last_processed: A :class:`~autogen_agentchat.base.TaskResult` if the stream is from :meth:`~autogen_agentchat.base.TaskRunner.run_stream`
            or a :class:`~autogen_agentchat.base.Response` if the stream is from :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream`.
    """
    render_image_iterm = _is_running_in_iterm() and _is_output_a_tty() and not no_inline_images
    start_time = time.time()
    total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
    rich_console = Console()

    last_processed: Optional[T] = None

    async for message in stream:
        if isinstance(message, TaskResult):
            duration = time.time() - start_time
            if output_stats:
                output = (
                    f"Number of messages: {len(message.messages)}\n"
                    f"Finish reason: {message.stop_reason}\n"
                    f"Total prompt tokens: {total_usage.prompt_tokens}\n"
                    f"Total completion tokens: {total_usage.completion_tokens}\n"
                    f"Duration: {duration:.2f} seconds\n"
                )
                await _aprint_panel(rich_console, output, "Summary")

            last_processed = message  # type: ignore

        elif isinstance(message, Response):
            duration = time.time() - start_time

            # Print final response.
            text_parts, image_parts = _extract_message_content(message.chat_message)
            if message.chat_message.models_usage:
                if output_stats:
                    text_parts.append(
                        f"[Prompt tokens: {message.chat_message.models_usage.prompt_tokens}, Completion tokens: {message.chat_message.models_usage.completion_tokens}]"
                    )
                total_usage.completion_tokens += message.chat_message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.chat_message.models_usage.prompt_tokens

            await _aprint_message_content(
                rich_console,
                text_parts,
                image_parts,
                message.chat_message.source,
                render_image_iterm=render_image_iterm,
            )

            # Print summary.
            if output_stats:
                num_inner_messages = len(message.inner_messages) if message.inner_messages is not None else 0
                output = (
                    f"Number of inner messages: {num_inner_messages}\n"
                    f"Total prompt tokens: {total_usage.prompt_tokens}\n"
                    f"Total completion tokens: {total_usage.completion_tokens}\n"
                    f"Duration: {duration:.2f} seconds\n"
                )
                await _aprint_panel(rich_console, output, "Summary")

            # mypy ignore
            last_processed = message  # type: ignore
        # We don't want to print UserInputRequestedEvent messages, we just use them to signal the user input event.
        elif isinstance(message, UserInputRequestedEvent):
            if user_input_manager is not None:
                user_input_manager.notify_event_received(message.request_id)
        elif isinstance(message, ModelClientStreamingChunkEvent):
            # TODO: Handle model client streaming chunk events.
            pass
        else:
            # Cast required for mypy to be happy
            message = cast(BaseAgentEvent | BaseChatMessage, message)  # type: ignore

            text_parts, image_parts = _extract_message_content(message)
            # Add usage stats if needed
            if message.models_usage:
                if output_stats:
                    text_parts.append(
                        f"[Prompt tokens: {message.models_usage.prompt_tokens}, Completion tokens: {message.models_usage.completion_tokens}]"
                    )
                total_usage.completion_tokens += message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.models_usage.prompt_tokens

            await _aprint_message_content(
                rich_console,
                text_parts,
                image_parts,
                message.source,
                render_image_iterm=render_image_iterm,
            )

    if last_processed is None:
        raise ValueError("No TaskResult or Response was processed.")

    return last_processed


# iTerm2 image rendering protocol: https://iterm2.com/documentation-images.html
def _image_to_iterm(image: Image) -> str:
    image_data = image.to_base64()
    return f"\033]1337;File=inline=1:{image_data}\a\n"
