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
from nbclient import NotebookClient
from nbformat import v4 as nbformat

from .._common import silence_pip


@dataclass
class JupyterCodeResult(CodeResult):
    """A code result class for Jupyter code executor."""

    output_files: list[Path]


class JupyterCodeExecutor(CodeExecutor):
    def __init__(
        self,
        kernel_name: str = "python3",
        timeout: int = 60,
        output_dir: Path = Path("."),
    ):
        """A code executor class that executes code statefully using nbclient.

        Args:
            kernel_name (str): The kernel name to use. By default, "python3".
            timeout (int): The timeout for code execution, by default 60.
            output_dir (Path): The directory to save output files, by default ".".
        """
        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        self._kernel_name = kernel_name
        self._timeout = timeout
        self._output_dir = output_dir
        self._start()

    async def execute_code_blocks(
        self, code_blocks: list[CodeBlock], cancellation_token: CancellationToken
    ) -> JupyterCodeResult:
        """Execute code blocks and return the result.

        Args:
            code_blocks (list[CodeBlock]): The code blocks to execute.

        Returns:
            JupyterCodeResult: The result of the code execution.
        """
        outputs: list[str] = []
        output_files: list[Path] = []
        exit_code = 0

        for code_block in code_blocks:
            result = await self._execute_code_block(code_block, cancellation_token)
            exit_code = result.exit_code
            outputs.append(result.output)
            output_files.extend(result.output_files)

        return JupyterCodeResult(exit_code=exit_code, output="\n".join(outputs), output_files=output_files)

    async def _execute_code_block(
        self, code_block: CodeBlock, cancellation_token: CancellationToken
    ) -> JupyterCodeResult:
        """Execute single code block and return the result.

        Args:
            code_block (CodeBlock): The code block to execute.

        Returns:
            JupyterCodeResult: The result of the code execution.
        """
        execute_task = asyncio.create_task(
            self._client.async_execute_cell_standalone(
                nbformat.new_code_cell(silence_pip(code_block.code, code_block.language)), cleanup_kc=False
            )
        )
        cancellation_token.link_future(execute_task)
        output_cell = await asyncio.wait_for(asyncio.shield(execute_task), timeout=self._timeout)

        outputs: list[str] = []
        output_files: list[Path] = []
        exit_code = 0

        for output in output_cell.get("outputs", []):
            match output.get("output_type"):
                case "stream":
                    outputs.append(output.get("text", ""))
                case "error":
                    traceback = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", "\n".join(output["traceback"]))
                    outputs.append(traceback)
                    exit_code = 1
                case "execute_result" | "display_data":
                    data = output.get("data", {})
                    for mime, content in data.items():
                        match mime:
                            case "text/plain":
                                outputs.append(content)
                            case "image/png":
                                path = self._save_image(content)
                                output_files.append(path)
                            case "image/jpeg":
                                # TODO: Should this also be encoded? Images are encoded as both png and jpg
                                pass
                            case "text/html":
                                path = self._save_html(content)
                                output_files.append(path)
                            case _:
                                outputs.append(json.dumps(content))

        return JupyterCodeResult(exit_code=exit_code, output="\n".join(outputs), output_files=output_files)

    def _save_image(self, image_data_base64: str) -> Path:
        """Save image data to a file."""
        image_data = base64.b64decode(image_data_base64)
        path = self._output_dir / f"{uuid.uuid4().hex}.png"
        path.write_bytes(image_data)
        return path.absolute()

    def _save_html(self, html_data: str) -> Path:
        """Save HTML data to a file."""
        path = self._output_dir / f"{uuid.uuid4().hex}.html"
        path.write_text(html_data)
        return path.absolute()

    async def restart(self) -> None:
        """Restart the code executor."""
        self._start()

    def _start(self) -> None:
        self._client = NotebookClient(
            nb=nbformat.new_notebook(), kernel_name=self._kernel_name, timeout=self._timeout, allow_errors=True
        )

    async def stop(self) -> None:
        """Stop the kernel."""
        if self._client.km is not None:
            await self._client._async_cleanup_kernel()  # type: ignore

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        await self.stop()
