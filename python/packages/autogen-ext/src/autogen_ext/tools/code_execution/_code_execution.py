from autogen_core import CancellationToken, Component, ComponentModel
from autogen_core.code_executor import CodeBlock, CodeExecutor
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field, model_serializer
from typing_extensions import Self


class CodeExecutionInput(BaseModel):
    code: str = Field(description="The contents of the Python code block that should be executed")


class CodeExecutionResult(BaseModel):
    success: bool
    output: str

    @model_serializer
    def ser_model(self) -> str:
        return self.output


class PythonCodeExecutionToolConfig(BaseModel):
    """Configuration for PythonCodeExecutionTool"""

    executor: ComponentModel
    description: str = "Execute Python code blocks."


class PythonCodeExecutionTool(
    BaseTool[CodeExecutionInput, CodeExecutionResult], Component[PythonCodeExecutionToolConfig]
):
    """A tool that executes Python code in a code executor and returns output.

    Example executors:

    * :class:`autogen_ext.code_executors.local.LocalCommandLineCodeExecutor`
    * :class:`autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor`
    * :class:`autogen_ext.code_executors.azure.ACADynamicSessionsCodeExecutor`

    Example usage:

    .. code-block:: bash

        pip install -U "autogen-agentchat" "autogen-ext[openai]" "yfinance" "matplotlib"

    .. code-block:: python

        import asyncio
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.ui import Console
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
        from autogen_ext.tools.code_execution import PythonCodeExecutionTool


        async def main() -> None:
            tool = PythonCodeExecutionTool(LocalCommandLineCodeExecutor(work_dir="coding"))
            agent = AssistantAgent(
                "assistant", OpenAIChatCompletionClient(model="gpt-4o"), tools=[tool], reflect_on_tool_use=True
            )
            await Console(
                agent.run_stream(
                    task="Create a plot of MSFT stock prices in 2024 and save it to a file. Use yfinance and matplotlib."
                )
            )


        asyncio.run(main())


    Args:
        executor (CodeExecutor): The code executor that will be used to execute the code blocks.
    """

    component_config_schema = PythonCodeExecutionToolConfig
    component_provider_override = "autogen_ext.tools.code_execution.PythonCodeExecutionTool"

    def __init__(self, executor: CodeExecutor):
        super().__init__(CodeExecutionInput, CodeExecutionResult, "CodeExecutor", "Execute Python code blocks.")
        self._executor = executor

    async def run(self, args: CodeExecutionInput, cancellation_token: CancellationToken) -> CodeExecutionResult:
        code_blocks = [CodeBlock(code=args.code, language="python")]
        result = await self._executor.execute_code_blocks(
            code_blocks=code_blocks, cancellation_token=cancellation_token
        )

        return CodeExecutionResult(success=result.exit_code == 0, output=result.output)

    def _to_config(self) -> PythonCodeExecutionToolConfig:
        """Convert current instance to config object"""
        return PythonCodeExecutionToolConfig(executor=self._executor.dump_component())

    @classmethod
    def _from_config(cls, config: PythonCodeExecutionToolConfig) -> Self:
        """Create instance from config object"""
        executor = CodeExecutor.load_component(config.executor)
        return cls(executor=executor)
