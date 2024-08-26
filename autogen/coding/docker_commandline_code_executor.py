# Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
#
# SPDX-License-Identifier: Apache-2.0
#
# Original portions of this file are derived from https://github.com/microsoft/autogen under the MIT License.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import atexit
import logging
import sys
import uuid
from hashlib import md5
from pathlib import Path
from time import sleep
from types import TracebackType
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

import docker
from docker.errors import ImageNotFound

from ..code_utils import TIMEOUT_MSG, _cmd
from .base import CodeBlock, CodeExecutor, CodeExtractor, CommandLineCodeResult
from .markdown_code_extractor import MarkdownCodeExtractor
from .utils import _get_file_name_from_content, silence_pip

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


def _wait_for_ready(container: Any, timeout: int = 60, stop_time: float = 0.1) -> None:
    elapsed_time = 0.0
    while container.status != "running" and elapsed_time < timeout:
        sleep(stop_time)
        elapsed_time += stop_time
        container.reload()
        continue
    if container.status != "running":
        raise ValueError("Container failed to start")


__all__ = ("DockerCommandLineCodeExecutor",)


class DockerCommandLineCodeExecutor(CodeExecutor):
    DEFAULT_EXECUTION_POLICY: ClassVar[Dict[str, bool]] = {
        "bash": True,
        "shell": True,
        "sh": True,
        "pwsh": True,
        "powershell": True,
        "ps1": True,
        "python": True,
        "javascript": False,
        "html": False,
        "css": False,
    }
    LANGUAGE_ALIASES: ClassVar[Dict[str, str]] = {"py": "python", "js": "javascript"}

    def __init__(
        self,
        image: str = "python:3-slim",
        container_name: Optional[str] = None,
        timeout: int = 60,
        work_dir: Union[Path, str] = Path("."),
        bind_dir: Optional[Union[Path, str]] = None,
        auto_remove: bool = True,
        stop_container: bool = True,
        execution_policies: Optional[Dict[str, bool]] = None,
    ):
        """(Experimental) A code executor class that executes code through
        a command line environment in a Docker container.

        The executor first saves each code block in a file in the working
        directory, and then executes the code file in the container.
        The executor executes the code blocks in the order they are received.
        Currently, the executor only supports Python and shell scripts.
        For Python code, use the language "python" for the code block.
        For shell scripts, use the language "bash", "shell", or "sh" for the code
        block.

        Args:
            image (_type_, optional): Docker image to use for code execution.
                Defaults to "python:3-slim".
            container_name (Optional[str], optional): Name of the Docker container
                which is created. If None, will autogenerate a name. Defaults to None.
            timeout (int, optional): The timeout for code execution. Defaults to 60.
            work_dir (Union[Path, str], optional): The working directory for the code
                execution. Defaults to Path(".").
            bind_dir (Union[Path, str], optional): The directory that will be bound
            to the code executor container. Useful for cases where you want to spawn
            the container from within a container. Defaults to work_dir.
            auto_remove (bool, optional): If true, will automatically remove the Docker
                container when it is stopped. Defaults to True.
            stop_container (bool, optional): If true, will automatically stop the
                container when stop is called, when the context manager exits or when
                the Python process exits with atext. Defaults to True.

        Raises:
            ValueError: On argument error, or if the container fails to start.
        """
        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        if isinstance(work_dir, str):
            work_dir = Path(work_dir)
        work_dir.mkdir(exist_ok=True)

        if bind_dir is None:
            bind_dir = work_dir
        elif isinstance(bind_dir, str):
            bind_dir = Path(bind_dir)

        client = docker.from_env()
        # Check if the image exists
        try:
            client.images.get(image)
        except ImageNotFound:
            logging.info(f"Pulling image {image}...")
            # Let the docker exception escape if this fails.
            client.images.pull(image)

        if container_name is None:
            container_name = f"autogen-code-exec-{uuid.uuid4()}"

        # Start a container from the image, read to exec commands later
        self._container = client.containers.create(
            image,
            name=container_name,
            entrypoint="/bin/sh",
            tty=True,
            auto_remove=auto_remove,
            volumes={str(bind_dir.resolve()): {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
        )
        self._container.start()

        _wait_for_ready(self._container)

        def cleanup() -> None:
            try:
                container = client.containers.get(container_name)
                container.stop()
            except docker.errors.NotFound:
                pass
            atexit.unregister(cleanup)

        if stop_container:
            atexit.register(cleanup)

        self._cleanup = cleanup

        # Check if the container is running
        if self._container.status != "running":
            raise ValueError(f"Failed to start container from image {image}. Logs: {self._container.logs()}")

        self._timeout = timeout
        self._work_dir: Path = work_dir
        self._bind_dir: Path = bind_dir
        self.execution_policies = self.DEFAULT_EXECUTION_POLICY.copy()
        if execution_policies is not None:
            self.execution_policies.update(execution_policies)

    @property
    def timeout(self) -> int:
        """(Experimental) The timeout for code execution."""
        return self._timeout

    @property
    def work_dir(self) -> Path:
        """(Experimental) The working directory for the code execution."""
        return self._work_dir

    @property
    def bind_dir(self) -> Path:
        """(Experimental) The binding directory for the code execution container."""
        return self._bind_dir

    @property
    def code_extractor(self) -> CodeExtractor:
        """(Experimental) Export a code extractor that can be used by an agent."""
        return MarkdownCodeExtractor()

    def execute_code_blocks(self, code_blocks: List[CodeBlock]) -> CommandLineCodeResult:
        """(Experimental) Execute the code blocks and return the result.

        Args:
            code_blocks (List[CodeBlock]): The code blocks to execute.

        Returns:
            CommandlineCodeResult: The result of the code execution."""

        if len(code_blocks) == 0:
            raise ValueError("No code blocks to execute.")

        outputs = []
        files = []
        last_exit_code = 0
        for code_block in code_blocks:
            lang = self.LANGUAGE_ALIASES.get(code_block.language.lower(), code_block.language.lower())
            if lang not in self.DEFAULT_EXECUTION_POLICY:
                outputs.append(f"Unsupported language {lang}\n")
                last_exit_code = 1
                break

            execute_code = self.execution_policies.get(lang, False)
            code = silence_pip(code_block.code, lang)

            # Check if there is a filename comment
            try:
                filename = _get_file_name_from_content(code, self._work_dir)
            except ValueError:
                outputs.append("Filename is not in the workspace")
                last_exit_code = 1
                break

            if not filename:
                filename = f"tmp_code_{md5(code.encode()).hexdigest()}.{lang}"

            code_path = self._work_dir / filename
            with code_path.open("w", encoding="utf-8") as fout:
                fout.write(code)
            files.append(code_path)

            if not execute_code:
                outputs.append(f"Code saved to {str(code_path)}\n")
                continue

            command = ["timeout", str(self._timeout), _cmd(lang), filename]
            result = self._container.exec_run(command)
            exit_code = result.exit_code
            output = result.output.decode("utf-8")
            if exit_code == 124:
                output += "\n" + TIMEOUT_MSG
            outputs.append(output)

            last_exit_code = exit_code
            if exit_code != 0:
                break

        code_file = str(files[0]) if files else None
        return CommandLineCodeResult(exit_code=last_exit_code, output="".join(outputs), code_file=code_file)

    def restart(self) -> None:
        """(Experimental) Restart the code executor."""
        self._container.restart()
        if self._container.status != "running":
            raise ValueError(f"Failed to restart container. Logs: {self._container.logs()}")

    def stop(self) -> None:
        """(Experimental) Stop the code executor."""
        self._cleanup()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        self.stop()
