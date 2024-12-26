import argparse
import asyncio
import os
import sys
import time
from typing import Any, AsyncGenerator, List, Optional, TypeVar, cast

from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import AgentEvent, ChatMessage, MultiModalMessage
from autogen_core import Image
from autogen_core.models import RequestUsage

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from rich.console import Console
from rich.panel import Panel
from rich.text import Text



def _is_running_in_iterm() -> bool:
    return os.getenv("TERM_PROGRAM") == "iTerm.app"


def _is_output_a_tty() -> bool:
    return sys.stdout.isatty()


T = TypeVar("T", bound=TaskResult | Response)


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


def _print(*args: Any, **kwargs: Any) -> None:
    print(*args, **kwargs)  # noqa: T201


async def CustomConsole(
    stream: AsyncGenerator[AgentEvent | ChatMessage | T, None],
    *,
    no_inline_images: bool = False,
) -> T:
    """
    Consumes the message stream from :meth:`~autogen_agentchat.base.TaskRunner.run_stream`
    or :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream` and renders the messages to the console using print().
    Returns the last processed TaskResult or Response.

    Args:
        stream (AsyncGenerator[AgentEvent | ChatMessage | TaskResult, None] | AsyncGenerator[AgentEvent | ChatMessage | Response, None]): Message stream to render.
            This can be from :meth:`~autogen_agentchat.base.TaskRunner.run_stream` or :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream`.
        no_inline_images (bool, optional): If terminal is iTerm2 will render images inline. Use this to disable this behavior. Defaults to False.

    Returns:
        last_processed: A :class:`~autogen_agentchat.base.TaskResult` if the stream is from :meth:`~autogen_agentchat.base.TaskRunner.run_stream`
            or a :class:`~autogen_agentchat.base.Response` if the stream is from :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream`.
    """
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

        elif isinstance(message, Response):
            duration = time.time() - start_time

            # Print final response.
            output = Text.from_markup(f"[bold]{message.chat_message.source}[/bold]\n{_message_to_str(message.chat_message, render_image_iterm=render_image_iterm)}")
            if message.chat_message.models_usage:
                output.append(f"\n[Prompt tokens: {message.chat_message.models_usage.prompt_tokens}, Completion tokens: {message.chat_message.models_usage.completion_tokens}]")
                total_usage.completion_tokens += message.chat_message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.chat_message.models_usage.prompt_tokens
            console.print(Panel(output))

            # Print summary.
            if message.inner_messages is not None:
                num_inner_messages = len(message.inner_messages)
            else:
                num_inner_messages = 0
            output = (
                f"Number of inner messages: {num_inner_messages}\n"
                f"Total prompt tokens: {total_usage.prompt_tokens}\n"
                f"Total completion tokens: {total_usage.completion_tokens}\n"
                f"Duration: {duration:.2f} seconds\n"
            )
            console.print(Panel(output, title="Summary"))
            last_processed = message  # type: ignore

        else:
            # Cast required for mypy to be happy
            message = cast(AgentEvent | ChatMessage, message)  # type: ignore
            output = Text.from_markup(f"[bold]{message.source}[/bold]\n{_message_to_str(message, render_image_iterm=render_image_iterm)}")
            if message.models_usage:
                output.append(f"\n[Prompt tokens: {message.models_usage.prompt_tokens}, Completion tokens: {message.models_usage.completion_tokens}]")
                total_usage.completion_tokens += message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.models_usage.prompt_tokens
            console.print(Panel(output))

    if last_processed is None:
        raise ValueError("No TaskResult or Response was processed.")

    return last_processed


def main() -> None:
    """
    Command-line interface for running a complex task using MagenticOne.

    This script accepts a single task string and an optional flag to disable
    human-in-the-loop mode. It initializes the necessary clients and runs the
    task using the MagenticOne class.

    Arguments:
    task (str): The task to be executed by MagenticOne.
    --no-hil: Optional flag to disable human-in-the-loop mode.

    Example usage:
    python magentic_one_cli.py "example task"
    python magentic_one_cli.py --no-hil "example task"
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run a complex task using MagenticOne.\n\n"
            "For more information, refer to the following paper: https://arxiv.org/abs/2411.04468"
        )
    )
    parser.add_argument("task", type=str, nargs=1, help="The task to be executed by MagenticOne.")
    parser.add_argument("--no-hil", action="store_true", help="Disable human-in-the-loop mode.")
    args = parser.parse_args()

    async def run_task(task: str, hil_mode: bool) -> None:
        client = OpenAIChatCompletionClient(model="gpt-4o")
        m1 = MagenticOne(client=client, hil_mode=hil_mode)
        await CustomConsole(m1.run_stream(task=task))

    task = args.task[0]
    asyncio.run(asyncio.wait_for(run_task(task, not args.no_hil), timeout=300))


if __name__ == "__main__":
    import os
    import sys

    fd = sys.stdout.fileno()
    flags = os.fcntl(fd, os.F_GETFL)
    os.fcntl(fd, os.F_SETFL, flags & ~os.O_NONBLOCK)

    main()
