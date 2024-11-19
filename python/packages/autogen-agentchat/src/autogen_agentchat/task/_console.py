import os
import sys
import time
from typing import AsyncGenerator, List

from autogen_core.components import Image
from autogen_core.components.models import RequestUsage

from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import AgentMessage, MultiModalMessage


def _is_running_in_iterm() -> bool:
    return os.getenv("TERM_PROGRAM") == "iTerm.app"


def _is_output_a_tty() -> bool:
    return sys.stdout.isatty()


async def Console(
    stream: AsyncGenerator[AgentMessage | TaskResult, None] | AsyncGenerator[AgentMessage | Response, None],
    *,
    no_inline_images: bool = False,
) -> None:
    """Consume the stream from  :meth:`~autogen_agentchat.base.Team.run_stream`
    or :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream`
    and print the messages to the console.

    Args:
        stream (AsyncGenerator[AgentMessage | TaskResult, None] | AsyncGenerator[AgentMessage | Response, None]): Stream to render
        no_inline_images (bool, optional): If terminal is iTerm2 will render images inline. Use this to disable this behavior. Defaults to False.
    """

    render_image_iterm = _is_running_in_iterm() and _is_output_a_tty() and not no_inline_images
    start_time = time.time()
    total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
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
        elif isinstance(message, Response):
            duration = time.time() - start_time

            # Print final response.
            output = f"{'-' * 10} {message.chat_message.source} {'-' * 10}\n{_message_to_str(message.chat_message, render_image_iterm=render_image_iterm)}\n"
            if message.chat_message.models_usage:
                output += f"[Prompt tokens: {message.chat_message.models_usage.prompt_tokens}, Completion tokens: {message.chat_message.models_usage.completion_tokens}]\n"
                total_usage.completion_tokens += message.chat_message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.chat_message.models_usage.prompt_tokens
            sys.stdout.write(output)

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
        else:
            output = f"{'-' * 10} {message.source} {'-' * 10}\n{_message_to_str(message, render_image_iterm=render_image_iterm)}\n"
            if message.models_usage:
                output += f"[Prompt tokens: {message.models_usage.prompt_tokens}, Completion tokens: {message.models_usage.completion_tokens}]\n"
                total_usage.completion_tokens += message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.models_usage.prompt_tokens
            sys.stdout.write(output)


# iTerm2 image rendering protocol: https://iterm2.com/documentation-images.html
def _image_to_iterm(image: Image) -> str:
    image_data = image.to_base64()
    return f"\033]1337;File=inline=1:{image_data}\a\n"


def _message_to_str(message: AgentMessage, *, render_image_iterm: bool = False) -> str:
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
