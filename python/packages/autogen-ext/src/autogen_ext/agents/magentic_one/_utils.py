"""Utility functions for MagenticOne agents."""

import asyncio
import shlex
from typing import List, Tuple

from autogen_core import CancellationToken

from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor


async def exec_command_umask_patched(
    self: DockerCommandLineCodeExecutor,
    command: List[str],
    cancellation_token: CancellationToken,
) -> Tuple[str, int]:
    """Execute command with umask 000 to ensure proper file permissions.

    This is a patched version of the execute command that sets umask 000
    before running the command to ensure files are created with proper permissions.
    """
    if self._container is None or not self._running:  # type: ignore
        raise ValueError(
            "Container is not running. Must first be started with either start or a context manager."
        )

    # wrap the original command in a shell so `umask` (a shell builtin) runs
    joined = shlex.join(command)
    shell_cmd = f"umask 000 && {joined}"
    command = ["sh", "-c", shell_cmd]

    exec_task = asyncio.create_task(
        asyncio.to_thread(self._container.exec_run, command)  # type: ignore
    )
    cancellation_token.link_future(exec_task)

    # Wait for the exec task to finish.
    try:
        result = await exec_task
        exit_code = result.exit_code
        output = result.output.decode("utf-8")
        if exit_code == 124:
            output += "\n Timeout"
        return output, exit_code
    except asyncio.CancelledError:
        # Schedule a task to kill the running command in the background.
        self._cancellation_tasks.append(  # type: ignore
            asyncio.create_task(self._kill_running_command(command))  # type: ignore
        )
        return "Code execution was cancelled.", 1
