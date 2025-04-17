import asyncio
import base64
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import List, Optional, Union

from autogen_core import CancellationToken, Component
from autogen_core.code_executor import CodeBlock, CodeExecutor, CodeResult
from autogen_ext.code_executors._common import silence_pip
from pydantic import BaseModel
from typing_extensions import Self

from ._jupyter_server import JupyterClient, JupyterConnectable, JupyterConnectionInfo, JupyterKernelClient


@dataclass
class DockerJupyterCodeResult(CodeResult):
    """(Experimental) A code result class for IPython code executor."""

    output_files: list[Path]


class DockerJupyterCodeExecutorConfig(BaseModel):
    """Configuration for JupyterCodeExecutor"""

    jupyter_server: Union[JupyterConnectable, JupyterConnectionInfo]
    kernel_name: str = "python3"
    timeout: int = 60
    output_dir: Optional[Union[Path, str]] = None

    class Config:
        arbitrary_types_allowed = True


class DockerJupyterCodeExecutor(CodeExecutor, Component[DockerJupyterCodeExecutorConfig]):
    """(Experimental) A code executor class that executes code statefully using
    a Jupyter server supplied to this class.

    Each execution is stateful and can access variables created from previous
    executions in the same session.

    To use this, you need to install the following dependencies:

    .. code-block:: shell

        pip install "autogen-ext[docker-jupyter-executor]"

    Example of using it directly:

    .. code-block:: python

        import asyncio
        from autogen_core.code_executor import CodeBlock
        from autogen_ext.code_executors.docker_jupyter import DockerJupyterCodeExecutor, DockerJupyterServer


        async def main() -> None:
            async with DockerJupyterServer() as jupyter_server:
                async with DockerJupyterCodeExecutor(jupyter_server=jupyter_server) as executor:
                    code_blocks = [CodeBlock(code="print('hello world!')", language="python")]
                    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token=CancellationToken())
                    print(code_result)


        asyncio.run(main())

    Example of using it with your own jupyter image:
    .. code-block:: python
        import asyncio
        from autogen_core.code_executor import CodeBlock
        from autogen_ext.code_executors.docker_jupyter import DockerJupyterCodeExecutor, DockerJupyterServer


        async def main() -> None:
            async with DockerJupyterServer(custom_image_name="your_custom_images_name", expose_port=8888) as jupyter_server:
                async with DockerJupyterCodeExecutor(jupyter_server=jupyter_server) as executor:
                    code_blocks = [CodeBlock(code="print('hello world!')", language="python")]
                    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token=CancellationToken())
                    print(code_result)


        asyncio.run(main())

    Example of using it with :class:`~autogen_ext.tools.code_execution.PythonCodeExecutionTool`:

    .. code-block:: python

        import asyncio
        from autogen_agentchat.agents import AssistantAgent
        from autogen_ext.code_executors.docker_jupyter import DockerJupyterCodeExecutor, DockerJupyterServer
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_ext.tools.code_execution import PythonCodeExecutionTool


        async def main() -> None:
            async with DockerJupyterServer() as jupyter_server:
                async with DockerJupyterCodeExecutor(jupyter_server=jupyter_server) as executor:
                    tool = PythonCodeExecutionTool(executor)
                    model_client = OpenAIChatCompletionClient(model="gpt-4o")
                    agent = AssistantAgent("assistant", model_client=model_client, tools=[tool])
                    result = await agent.run(task="What is the 10th Fibonacci number? Use Python to calculate it.")
                    print(result)


        asyncio.run(main())

    Example of using it inside a :class:`~autogen_agentchat.agents._code_executor_agent.CodeExecutorAgent`:

    .. code-block:: python

        import asyncio
        from autogen_agentchat.agents import CodeExecutorAgent
        from autogen_agentchat.messages import TextMessage
        from autogen_ext.code_executors.docker_jupyter import DockerJupyterCodeExecutor, DockerJupyterServer
        from autogen_core import CancellationToken


        async def main() -> None:
            async with  DockerJupyterServer() as jupyter_server:
                async with DockerJupyterCodeExecutor(jupyter_server=jupyter_server) as executor:
                    code_executor_agent = CodeExecutorAgent("code_executor", code_executor=executor)
                    task = TextMessage(
                        content='''Here is some code
                ```python
                print('Hello world')
                ```
                ''',
                        source="user",
                    )
                    response = await code_executor_agent.on_messages([task], CancellationToken())
                    print(response.chat_message)


        asyncio.run(main())
    Args:
        jupyter_server (Union[JupyterConnectable, JupyterConnectionInfo]): The Jupyter server to use.
        kernel_name (str): The kernel name to use. Make sure it is installed.
            By default, it is "python3".
        timeout (int): The timeout for code execution, by default 60.
        output_dir (str): The directory to save output files, by default None.
    """

    component_config_schema = DockerJupyterCodeExecutorConfig
    component_provider_override = "autogen_ext.code_executors.docker_jupyter.DockerJupyterCodeExecutor"

    def __init__(
        self,
        jupyter_server: Union[JupyterConnectable, JupyterConnectionInfo],
        kernel_name: str = "python3",
        timeout: int = 60,
        output_dir: Path | None = None,
    ):
        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        if isinstance(jupyter_server, JupyterConnectable):
            self._connection_info = jupyter_server.connection_info
        elif isinstance(jupyter_server, JupyterConnectionInfo):
            self._connection_info = jupyter_server
        else:
            raise ValueError("jupyter_server must be a JupyterConnectable or JupyterConnectionInfo.")

        self._output_dir = output_dir or getattr(jupyter_server, "_bind_dir", None)
        if not self._output_dir:
            with tempfile.TemporaryDirectory() as temp_dir:
                self._output_dir = Path(temp_dir)
                self._output_dir.mkdir(exist_ok=True)

        self._jupyter_client = JupyterClient(self._connection_info)

        self._kernel_name = kernel_name
        self._timeout = timeout
        self._async_jupyter_kernel_client: Optional[JupyterKernelClient] = None
        self._kernel_id: Optional[str] = None

    async def _ensure_async_kernel_client(self) -> JupyterKernelClient:
        """Ensure that an async kernel client exists and return it."""
        if self._kernel_id is None:
            await self.start()
            assert self._kernel_id is not None
        if self._async_jupyter_kernel_client is None:
            self._async_jupyter_kernel_client = await self._jupyter_client.get_kernel_client(self._kernel_id)
        return self._async_jupyter_kernel_client

    async def execute_code_blocks(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> DockerJupyterCodeResult:
        """(Experimental) Execute a list of code blocks and return the result.

        This method executes a list of code blocks as cells in the Jupyter kernel.
        See: https://jupyter-client.readthedocs.io/en/stable/messaging.html
        for the message protocol.

        Args:
            code_blocks (List[CodeBlock]): A list of code blocks to execute.

        Returns:
            DockerJupyterCodeResult: The result of the code execution.
        """
        kernel_client = await self._ensure_async_kernel_client()
        # Wait for kernel to be ready using async client
        is_ready = await kernel_client.wait_for_ready(timeout_seconds=self._timeout)
        if not is_ready:
            return DockerJupyterCodeResult(exit_code=1, output="ERROR: Kernel not ready", output_files=[])

        outputs: List[str] = []
        output_files: List[Path] = []
        for code_block in code_blocks:
            code = silence_pip(code_block.code, code_block.language)
            # Execute code using async client
            exec_task = asyncio.create_task(kernel_client.execute(code, timeout_seconds=self._timeout))
            cancellation_token.link_future(exec_task)
            result = await exec_task
            if result.is_ok:
                outputs.append(result.output)
                for data in result.data_items:
                    if data.mime_type == "image/png":
                        path = self._save_image(data.data)
                        outputs.append(path)
                        output_files.append(Path(path))
                    elif data.mime_type == "text/html":
                        path = self._save_html(data.data)
                        outputs.append(path)
                        output_files.append(Path(path))
                    else:
                        outputs.append(json.dumps(data.data))
            else:
                return DockerJupyterCodeResult(exit_code=1, output=f"ERROR: {result.output}", output_files=output_files)
        return DockerJupyterCodeResult(
            exit_code=0, output="\n".join([str(output) for output in outputs]), output_files=output_files
        )

    async def restart(self) -> None:
        """(Experimental) Restart a new session."""
        # Use async client to restart kernel
        if self._kernel_id is not None:
            await self._jupyter_client.restart_kernel(self._kernel_id)
        # Reset the clients to force recreation
        if self._async_jupyter_kernel_client is not None:
            await self._async_jupyter_kernel_client.stop()
            self._async_jupyter_kernel_client = None

    async def start(self) -> None:
        """(Experimental) Start a new session."""
        available_kernels = await self._jupyter_client.list_kernel_specs()
        if self._kernel_name not in available_kernels["kernelspecs"]:
            raise ValueError(f"Kernel {self._kernel_name} is not installed.")
        self._kernel_id = await self._jupyter_client.start_kernel(self._kernel_name)

    def _save_image(self, image_data_base64: str) -> str:
        """Save image data to a file."""
        image_data = base64.b64decode(image_data_base64)
        filename = f"{uuid.uuid4().hex}.png"
        path = os.path.join(str(self._output_dir), filename)
        with open(path, "wb") as f:
            f.write(image_data)
        return os.path.abspath(path)

    def _save_html(self, html_data: str) -> str:
        """Save html data to a file."""
        filename = f"{uuid.uuid4().hex}.html"
        path = os.path.join(str(self._output_dir), filename)
        with open(path, "w") as f:
            f.write(html_data)
        return os.path.abspath(path)

    async def stop(self) -> None:
        """Stop the kernel."""
        if self._kernel_id is not None:
            await self._jupyter_client.delete_kernel(self._kernel_id)
        if self._async_jupyter_kernel_client is not None:
            await self._async_jupyter_kernel_client.stop()
            self._async_jupyter_kernel_client = None
        await self._jupyter_client.close()

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.stop()
