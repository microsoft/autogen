import asyncio
import base64
import json
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock, CodeExecutor, CodeResult

from .._common import silence_pip
from ._jupyter_connectable import JupyterConnectable


@dataclass
class JupyterCodeResult(CodeResult):
    """A code result class for Jupyter code executor."""

    output_files: list[Path]


class JupyterCodeExecutor(CodeExecutor):
    def __init__(
        self,
        server: JupyterConnectable,
        kernel_name: str = "python3",
        timeout: int = 60,
        output_dir: Path = Path("."),
    ):
        """A code executor class that executes code statefully using
        a Jupyter server supplied to this class.

        Each execution is stateful and can access variables created from previous
        executions in the same session.

        Args:
            server (JupyterConnectable): The Jupyter server to use.
            kernel_name (str): The kernel name to use. Make sure it is installed.
                By default, it is "python3".
            timeout (int): The timeout for code execution, by default 60.
            output_dir (Path): The directory to save output files, by default ".".
        """
        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        self._jupyter_client = server.get_client()
        self._kernel_name = kernel_name
        self._timeout = timeout
        self._output_dir = output_dir
        self.start()

    async def execute_code_blocks(
        self, code_blocks: list[CodeBlock], cancellation_token: CancellationToken
    ) -> JupyterCodeResult:
        """Execute code blocks and return the result.

        Args:
            code_blocks (list[CodeBlock]): The code blocks to execute.

        Returns:
            JupyterCodeResult: The result of the code execution.

        Raises:
            asyncio.TimeoutError: Code execution timeouts
            asyncio.CancelledError: CancellationToken evoked during execution
        """
        if self._kernel_id is None:
            raise ValueError("Kernel not running")

        async with await self._jupyter_client.get_kernel_client(self._kernel_id) as kernel_client:
            wait_for_ready_task = asyncio.create_task(kernel_client.wait_for_ready())
            cancellation_token.link_future(wait_for_ready_task)
            await asyncio.wait_for(wait_for_ready_task, timeout=self._timeout)

            outputs: list[str] = []
            output_files: list[Path] = []
            exit_code = 0

            for code_block in code_blocks:
                code = silence_pip(code_block.code, code_block.language)
                execute_task = asyncio.create_task(kernel_client.execute(code))
                cancellation_token.link_future(execute_task)
                result = await asyncio.wait_for(execute_task, timeout=self._timeout)

                # Clean ansi escape sequences
                result.output = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", result.output)
                outputs.append(result.output)

                if not result.is_ok:
                    exit_code = 1
                    break

                for data in result.data_items:
                    match data.mime_type:
                        case "image/png":
                            path = self._save_image(data.data)
                            output_files.append(path)
                        case "image/jpeg":
                            # TODO: Should this also be encoded? Images are encoded as both png and jpg
                            pass
                        case "text/html":
                            path = self._save_html(data.data)
                            output_files.append(path)
                        case _:
                            outputs.append(json.dumps(data.data))

            return JupyterCodeResult(exit_code=exit_code, output="\n".join(outputs), output_files=output_files)

    async def restart(self) -> None:
        """Restart the code executor."""
        if self._kernel_id is None:
            self.start()
        else:
            self._jupyter_client.restart_kernel(self._kernel_id)
            self._jupyter_kernel_client = self._jupyter_client.get_kernel_client(self._kernel_id)

    def start(self) -> None:
        """Start the kernel."""
        available_kernels = self._jupyter_client.list_kernel_specs()
        if self._kernel_name not in available_kernels["kernelspecs"]:
            raise ValueError(f"Kernel {self._kernel_name} is not installed.")

        self._kernel_id = self._jupyter_client.start_kernel(self._kernel_name)

    def stop(self) -> None:
        """Stop the kernel."""
        if self._kernel_id is not None:
            self._jupyter_client.delete_kernel(self._kernel_id)
            self._kernel_id = None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        self.stop()

    def _save_image(self, image_data_base64: str) -> Path:
        """Save image data to a file."""
        image_data = base64.b64decode(image_data_base64)
        path = self._output_dir / f"{uuid.uuid4().hex}.png"
        path.write_bytes(image_data)
        return path.absolute()

    def _save_html(self, html_data: str) -> Path:
        """Save html data to a file."""
        path = self._output_dir / f"{uuid.uuid4().hex}.html"
        path.write_text(html_data)
        return path.absolute()
