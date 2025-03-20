import asyncio
import base64
import json
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

from autogen_core import Component
from pydantic import BaseModel

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock, CodeExecutor, CodeResult
from nbclient import NotebookClient
from nbformat import NotebookNode
from nbformat import v4 as nbformat
from typing_extensions import Self

from .._common import silence_pip


@dataclass
class JupyterCodeResult(CodeResult):
    """A code result class for Jupyter code executor."""

    output_files: list[Path]


class JupyterCodeExecutorConfig(BaseModel):
    """Configuration for JupyterCodeExecutor"""

    kernel_name: str = "python3"
    timeout: int = 60
    output_dir: str = "."


class JupyterCodeExecutor(CodeExecutor, Component[JupyterCodeExecutorConfig]):
    """A code executor class that executes code statefully using [nbclient](https://github.com/jupyter/nbclient).

    .. danger::

        This will execute code on the local machine. If being used with LLM generated code, caution should be used.

    Example of using it directly:

    .. code-block:: python

        import asyncio
        from autogen_core import CancellationToken
        from autogen_core.code_executor import CodeBlock
        from autogen_ext.code_executors.jupyter import JupyterCodeExecutor


        async def main() -> None:
            async with JupyterCodeExecutor() as executor:
                cancel_token = CancellationToken()
                code_blocks = [CodeBlock(code="print('hello world!')", language="python")]
                code_result = await executor.execute_code_blocks(code_blocks, cancel_token)
                print(code_result)


        asyncio.run(main())

    Example of using it with :class:`~autogen_ext.tools.code_execution.PythonCodeExecutionTool`:

    .. code-block:: python

        import asyncio
        from autogen_agentchat.agents import AssistantAgent
        from autogen_ext.code_executors.jupyter import JupyterCodeExecutor
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_ext.tools.code_execution import PythonCodeExecutionTool


        async def main() -> None:
            async with JupyterCodeExecutor() as executor:
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
        from autogen_ext.code_executors.jupyter import JupyterCodeExecutor
        from autogen_core import CancellationToken


        async def main() -> None:
            async with JupyterCodeExecutor() as executor:
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
        kernel_name (str): The kernel name to use. By default, "python3".
        timeout (int): The timeout for code execution, by default 60.
        output_dir (Path): The directory to save output files, by default ".".
    """

    component_config_schema = JupyterCodeExecutorConfig
    component_provider_override = "autogen_ext.code_executors.jupyter.JupyterCodeExecutor"

    def __init__(
        self,
        kernel_name: str = "python3",
        timeout: int = 60,
        output_dir: Path = Path("."),
    ):
        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        self._kernel_name = kernel_name
        self._timeout = timeout
        self._output_dir = output_dir
        # TODO: Forward arguments perhaps?
        self._client = NotebookClient(
            nb=nbformat.new_notebook(),  # type: ignore
            kernel_name=self._kernel_name,
            timeout=self._timeout,
            allow_errors=True,
        )

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

            # Stop execution if one code block fails
            if exit_code != 0:
                break

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
            self._execute_cell(
                nbformat.new_code_cell(silence_pip(code_block.code, code_block.language))  # type: ignore
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
                case _:
                    pass

        return JupyterCodeResult(exit_code=exit_code, output="\n".join(outputs), output_files=output_files)

    async def _execute_cell(self, cell: NotebookNode) -> NotebookNode:
        # Temporary push cell to nb as async_execute_cell expects it. But then we want to remove it again as cells can take up significant amount of memory (especially with images)
        self._client.nb.cells.append(cell)
        output = await self._client.async_execute_cell(
            cell,
            cell_index=0,
        )
        self._client.nb.cells.pop()
        return output

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
        await self.stop()
        await self.start()

    async def start(self) -> None:
        self.kernel_context = self._client.async_setup_kernel()
        await self.kernel_context.__aenter__()

    async def stop(self) -> None:
        """Stop the kernel."""
        await self.kernel_context.__aexit__(None, None, None)

    def _to_config(self) -> JupyterCodeExecutorConfig:
        """Convert current instance to config object"""
        return JupyterCodeExecutorConfig(
            kernel_name=self._kernel_name, timeout=self._timeout, output_dir=str(self._output_dir)
        )

    @classmethod
    def _from_config(cls, config: JupyterCodeExecutorConfig) -> Self:
        """Create instance from config object"""
        return cls(kernel_name=config.kernel_name, timeout=config.timeout, output_dir=Path(config.output_dir))
