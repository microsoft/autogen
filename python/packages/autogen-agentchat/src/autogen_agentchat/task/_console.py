import sys
import time
from typing import AsyncGenerator

from autogen_core.components.models import RequestUsage

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import AgentMessage


async def Console(stream: AsyncGenerator[AgentMessage | TaskResult, None]) -> None:
    """Consume the stream from  :meth:`~autogen_agentchat.teams.Team.run_stream`
    and print the messages to the console."""

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
        else:
            output = f"{'-' * 10} {message.source} {'-' * 10}\n{message.content}\n"
            if message.models_usage:
                output += f"[Prompt tokens: {message.models_usage.prompt_tokens}, Completion tokens: {message.models_usage.completion_tokens}]\n"
                total_usage.completion_tokens += message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.models_usage.prompt_tokens
            sys.stdout.write(output)
