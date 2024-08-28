import base64
import json
import os
import re
import uuid
from pathlib import Path
from queue import Empty
from typing import Any, ClassVar, List

from jupyter_client import KernelManager  # type: ignore[attr-defined]
from jupyter_client.kernelspec import KernelSpecManager
from pydantic import BaseModel, Field, field_validator

from ...agentchat.agent import LLMAgent
from ..base import CodeBlock, CodeExtractor, IPythonCodeResult
from ..markdown_code_extractor import MarkdownCodeExtractor

__all__ = "EmbeddedIPythonCodeExecutor"


class EmbeddedIPythonCodeExecutor(BaseModel):
    """(Experimental) A code executor class that executes code statefully using an embedded
    IPython kernel managed by this class.

    **This will execute LLM generated code on the local machine.**

    Each execution is stateful and can access variables created from previous
    executions in the same session. The kernel must be installed before using
    this class. The kernel can be installed using the following command:
    `python -m ipykernel install --user --name {kernel_name}`
    where `kernel_name` is the name of the kernel to install.

    Args:
        timeout (int): The timeout for code execution, by default 60.
        kernel_name (str): The kernel name to use. Make sure it is installed.
            By default, it is "python3".
        output_dir (str): The directory to save output files, by default ".".
    """

    timeout: int = Field(default=60, ge=1, description="The timeout for code execution.")
    kernel_name: str = Field(default="python3", description="The kernel name to use. Make sure it is installed.")
    output_dir: str = Field(default=".", description="The directory to save output files.")

    @field_validator("output_dir")
    @classmethod
    def _output_dir_must_exist(cls, value: str) -> str:
        if not os.path.exists(value):
            raise ValueError(f"Output directory {value} does not exist.")
        return value

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        # Check if the kernel is installed.
        if self.kernel_name not in KernelSpecManager().find_kernel_specs():
            raise ValueError(
                f"Kernel {self.kernel_name} is not installed. "
                "Please first install it with "
                f"`python -m ipykernel install --user --name {self.kernel_name}`."
            )
        self._kernel_manager = KernelManager(kernel_name=self.kernel_name)
        self._kernel_manager.start_kernel()
        self._kernel_client = self._kernel_manager.client()
        self._kernel_client.start_channels()
        self._timeout = self.timeout
        self._kernel_name = self.kernel_name
        self._output_dir = Path(self.output_dir)

    @property
    def code_extractor(self) -> CodeExtractor:
        """(Experimental) Export a code extractor that can be used by an agent."""
        return MarkdownCodeExtractor()

    def execute_code_blocks(self, code_blocks: List[CodeBlock]) -> IPythonCodeResult:
        """(Experimental) Execute a list of code blocks and return the result.

        This method executes a list of code blocks as cells in an IPython kernel
        managed by this class.
        See: https://jupyter-client.readthedocs.io/en/stable/messaging.html
        for the message protocol.

        Args:
            code_blocks (List[CodeBlock]): A list of code blocks to execute.

        Returns:
            IPythonCodeResult: The result of the code execution.
        """
        self._kernel_client.wait_for_ready()
        outputs = []
        output_files = []
        for code_block in code_blocks:
            code = self._process_code(code_block.code)
            self._kernel_client.execute(code, store_history=True)
            while True:
                try:
                    msg = self._kernel_client.get_iopub_msg(timeout=self._timeout)
                    msg_type = msg["msg_type"]
                    content = msg["content"]
                    if msg_type in ["execute_result", "display_data"]:
                        for data_type, data in content["data"].items():
                            if data_type == "text/plain":
                                # Output is a text.
                                outputs.append(data)
                            elif data_type.startswith("image/"):
                                # Output is an image.
                                path = self._save_image(data)
                                outputs.append(f"Image data saved to {path}")
                                output_files.append(path)
                            elif data_type == "text/html":
                                # Output is an html.
                                path = self._save_html(data)
                                outputs.append(f"HTML data saved to {path}")
                                output_files.append(path)
                            else:
                                # Output raw data.
                                outputs.append(json.dumps(data))
                    elif msg_type == "stream":
                        # Output is a text.
                        outputs.append(content["text"])
                    elif msg_type == "error":
                        # Output is an error.
                        return IPythonCodeResult(
                            exit_code=1,
                            output=f"ERROR: {content['ename']}: {content['evalue']}\n{content['traceback']}",
                        )
                    if msg_type == "status" and content["execution_state"] == "idle":
                        break
                # handle time outs.
                except Empty:
                    return IPythonCodeResult(
                        exit_code=1,
                        output=f"ERROR: Timeout waiting for output from code block: {code_block.code}",
                    )
        # We return the full output.
        return IPythonCodeResult(
            exit_code=0, output="\n".join([str(output) for output in outputs]), output_files=output_files
        )

    def restart(self) -> None:
        """(Experimental) Restart a new session."""
        self._kernel_client.stop_channels()
        self._kernel_manager.shutdown_kernel()
        self._kernel_manager = KernelManager(kernel_name=self.kernel_name)
        self._kernel_manager.start_kernel()
        self._kernel_client = self._kernel_manager.client()
        self._kernel_client.start_channels()

    def _save_image(self, image_data_base64: str) -> str:
        """Save image data to a file."""
        image_data = base64.b64decode(image_data_base64)
        # Randomly generate a filename.
        filename = f"{uuid.uuid4().hex}.png"
        path = os.path.join(self.output_dir, filename)
        with open(path, "wb") as f:
            f.write(image_data)
        return os.path.abspath(path)

    def _save_html(self, html_data: str) -> str:
        """Save html data to a file."""
        # Randomly generate a filename.
        filename = f"{uuid.uuid4().hex}.html"
        path = os.path.join(self.output_dir, filename)
        with open(path, "w") as f:
            f.write(html_data)
        return os.path.abspath(path)

    def _process_code(self, code: str) -> str:
        """Process code before execution."""
        # Find lines that start with `! pip install` and make sure "-qqq" flag is added.
        lines = code.split("\n")
        for i, line in enumerate(lines):
            # use regex to find lines that start with `! pip install` or `!pip install`.
            match = re.search(r"^! ?pip install", line)
            if match is not None:
                if "-qqq" not in line:
                    lines[i] = line.replace(match.group(0), match.group(0) + " -qqq")
        return "\n".join(lines)
