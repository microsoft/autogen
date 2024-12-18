import os
import sys
import time
from typing import AsyncGenerator, List, Optional, TypeVar, cast

from autogen_core import Image
from autogen_core.models import RequestUsage

from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import AgentEvent, ChatMessage, MultiModalMessage


def _is_running_in_iterm() -> bool:
    return os.getenv("TERM_PROGRAM") == "iTerm.app"


def _is_output_a_tty() -> bool:
    return sys.stdout.isatty()


T = TypeVar("T", bound=TaskResult | Response)


async def Console(
    stream: AsyncGenerator[AgentEvent | ChatMessage | T, None],
    *,
    no_inline_images: bool = False,
) -> T:
    """
    Consumes the message stream from :meth:`~autogen_agentchat.base.TaskRunner.run_stream`
    or :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream` and renders the messages to the console.
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

    async for message in stream:
        if isinstance(message, TaskResult):
            duration = time.time() - start_time
            output = (
                f"{'-' * 10} Summary {'-' * 10}\n"
                f"Number of messages: {len(message.messages)}\n"
                f"Finish reason: {message.stop_reason}\n"
                f"Total prompt tokens: {total_usage.prompt_tokens}\n"
                f"Total completion tokens: {total_usage.completion_tokens}\n"
                f"Duration: {duration:.2f} seconds\n"
            )
            sys.stdout.write(output)
            sys.stdout.flush()
            # mypy ignore
            last_processed = message  # type: ignore

        elif isinstance(message, Response):
            duration = time.time() - start_time

            # Print final response.
            output = f"{'-' * 10} {message.chat_message.source} {'-' * 10}\n{_message_to_str(message.chat_message, render_image_iterm=render_image_iterm)}\n"
            if message.chat_message.models_usage:
                output += f"[Prompt tokens: {message.chat_message.models_usage.prompt_tokens}, Completion tokens: {message.chat_message.models_usage.completion_tokens}]\n"
                total_usage.completion_tokens += message.chat_message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.chat_message.models_usage.prompt_tokens
            sys.stdout.write(output)
            sys.stdout.flush()

            # Print summary.
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
            sys.stdout.write(output)
            sys.stdout.flush()
            # mypy ignore
            last_processed = message  # type: ignore

        else:
            # Cast required for mypy to be happy
            message = cast(AgentEvent | ChatMessage, message)  # type: ignore
            output = f"{'-' * 10} {message.source} {'-' * 10}\n{_message_to_str(message, render_image_iterm=render_image_iterm)}\n"
            if message.models_usage:
                output += f"[Prompt tokens: {message.models_usage.prompt_tokens}, Completion tokens: {message.models_usage.completion_tokens}]\n"
                total_usage.completion_tokens += message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.models_usage.prompt_tokens
            sys.stdout.write(output)
            sys.stdout.flush()

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
