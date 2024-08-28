import base64
import json
import os
import re
import sys
import uuid
from pathlib import Path
from types import TracebackType
from typing import Any, ClassVar, List, Optional, Type, Union

from autogen.coding.utils import silence_pip

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


from ...agentchat.agent import LLMAgent
from ..base import CodeBlock, CodeExecutor, CodeExtractor, IPythonCodeResult
from ..markdown_code_extractor import MarkdownCodeExtractor
from .base import JupyterConnectable, JupyterConnectionInfo
from .jupyter_client import JupyterClient


class JupyterCodeExecutor(CodeExecutor):
    def __init__(
        self,
        jupyter_server: Union[JupyterConnectable, JupyterConnectionInfo],
        kernel_name: str = "python3",
        timeout: int = 60,
        output_dir: Union[Path, str] = Path("."),
    ):
        """(Experimental) A code executor class that executes code statefully using
        a Jupyter server supplied to this class.

        Each execution is stateful and can access variables created from previous
        executions in the same session.

        Args:
            jupyter_server (Union[JupyterConnectable, JupyterConnectionInfo]): The Jupyter server to use.
            timeout (int): The timeout for code execution, by default 60.
            kernel_name (str): The kernel name to use. Make sure it is installed.
                By default, it is "python3".
            output_dir (str): The directory to save output files, by default ".".
        """
        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        if not output_dir.exists():
            raise ValueError(f"Output directory {output_dir} does not exist.")

        if isinstance(jupyter_server, JupyterConnectable):
            self._connection_info = jupyter_server.connection_info
        elif isinstance(jupyter_server, JupyterConnectionInfo):
            self._connection_info = jupyter_server
        else:
            raise ValueError("jupyter_server must be a JupyterConnectable or JupyterConnectionInfo.")

        self._jupyter_client = JupyterClient(self._connection_info)
        available_kernels = self._jupyter_client.list_kernel_specs()
        if kernel_name not in available_kernels["kernelspecs"]:
            raise ValueError(f"Kernel {kernel_name} is not installed.")

        self._kernel_id = self._jupyter_client.start_kernel(kernel_name)
        self._kernel_name = kernel_name
        self._jupyter_kernel_client = self._jupyter_client.get_kernel_client(self._kernel_id)
        self._timeout = timeout
        self._output_dir = output_dir

    @property
    def code_extractor(self) -> CodeExtractor:
        """(Experimental) Export a code extractor that can be used by an agent."""
        return MarkdownCodeExtractor()

    def execute_code_blocks(self, code_blocks: List[CodeBlock]) -> IPythonCodeResult:
        """(Experimental) Execute a list of code blocks and return the result.

        This method executes a list of code blocks as cells in the Jupyter kernel.
        See: https://jupyter-client.readthedocs.io/en/stable/messaging.html
        for the message protocol.

        Args:
            code_blocks (List[CodeBlock]): A list of code blocks to execute.

        Returns:
            IPythonCodeResult: The result of the code execution.
        """
        self._jupyter_kernel_client.wait_for_ready()
        outputs = []
        output_files = []
        for code_block in code_blocks:
            code = silence_pip(code_block.code, code_block.language)
            result = self._jupyter_kernel_client.execute(code, timeout_seconds=self._timeout)
            if result.is_ok:
                outputs.append(result.output)
                for data in result.data_items:
                    if data.mime_type == "image/png":
                        path = self._save_image(data.data)
                        outputs.append(f"Image data saved to {path}")
                        output_files.append(path)
                    elif data.mime_type == "text/html":
                        path = self._save_html(data.data)
                        outputs.append(f"HTML data saved to {path}")
                        output_files.append(path)
                    else:
                        outputs.append(json.dumps(data.data))
            else:
                return IPythonCodeResult(
                    exit_code=1,
                    output=f"ERROR: {result.output}",
                )

        return IPythonCodeResult(
            exit_code=0, output="\n".join([str(output) for output in outputs]), output_files=output_files
        )

    def restart(self) -> None:
        """(Experimental) Restart a new session."""
        self._jupyter_client.restart_kernel(self._kernel_id)
        self._jupyter_kernel_client = self._jupyter_client.get_kernel_client(self._kernel_id)

    def _save_image(self, image_data_base64: str) -> str:
        """Save image data to a file."""
        image_data = base64.b64decode(image_data_base64)
        # Randomly generate a filename.
        filename = f"{uuid.uuid4().hex}.png"
        path = os.path.join(self._output_dir, filename)
        with open(path, "wb") as f:
            f.write(image_data)
        return os.path.abspath(path)

    def _save_html(self, html_data: str) -> str:
        """Save html data to a file."""
        # Randomly generate a filename.
        filename = f"{uuid.uuid4().hex}.html"
        path = os.path.join(self._output_dir, filename)
        with open(path, "w") as f:
            f.write(html_data)
        return os.path.abspath(path)

    def stop(self) -> None:
        """Stop the kernel."""
        self._jupyter_client.delete_kernel(self._kernel_id)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        self.stop()
