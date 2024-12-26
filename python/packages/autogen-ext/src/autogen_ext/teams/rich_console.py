import os
import sys
import time
from typing import AsyncGenerator, List, Optional, TypeVar, cast

from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import AgentEvent, ChatMessage, MultiModalMessage
from autogen_core import Image
from autogen_core.models import RequestUsage
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

T = TypeVar("T", bound=TaskResult | Response)


def _is_running_in_iterm() -> bool:
    return os.getenv("TERM_PROGRAM") == "iTerm.app"


def _is_output_a_tty() -> bool:
    return sys.stdout.isatty()


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
                result.append("<image>")
        return "\n".join(result)
    else:
        return f"{message.content}"


async def RichConsole(
    stream: AsyncGenerator[AgentEvent | ChatMessage | T, None],
    *,
    no_inline_images: bool = False,
    primary_color: str = "magenta",
) -> T:
    render_image_iterm = _is_running_in_iterm() and _is_output_a_tty() and not no_inline_images
    start_time = time.time()
    total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    last_processed: Optional[T] = None
    console = Console()

    async for message in stream:
        if isinstance(message, TaskResult):
            duration = time.time() - start_time
            output = (
                f"Number of messages: {len(message.messages)}\n"
                f"Finish reason: {message.stop_reason}\n"
                f"Total prompt tokens: {total_usage.prompt_tokens}\n"
                f"Total completion tokens: {total_usage.completion_tokens}\n"
                f"Duration: {duration:.2f} seconds\n"
            )
            console.print(Panel(output, title="Summary"))
            last_processed = message  # type: ignore
        else:
            message = cast(AgentEvent | ChatMessage, message)  # type: ignore
            output = Text.from_markup(f"{_message_to_str(message, render_image_iterm=render_image_iterm)}")
            if message.models_usage:
                output.append(
                    f"\n[Prompt tokens: {message.models_usage.prompt_tokens}, Completion tokens: {message.models_usage.completion_tokens}]"
                )
                total_usage.completion_tokens += message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.models_usage.prompt_tokens
            console.print(Panel(output, title=f"[bold {primary_color}]{message.source}[/bold {primary_color}]"))
            if render_image_iterm and isinstance(message, MultiModalMessage):
                for c in message.content:
                    if isinstance(c, Image):
                        print(_image_to_iterm(c))

    if last_processed is None:
        raise ValueError("No TaskResult or Response was processed.")

    return last_processed
