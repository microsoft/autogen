import asyncio
import functools

from pydantic import BaseModel, Field, model_serializer

from ...core import CancellationToken
from ..code_executor import CodeBlock, CodeExecutor
from ._base import BaseTool


class CodeExecutionInput(BaseModel):
    code: str = Field(description="The contents of the Python code block that should be executed")


class CodeExecutionResult(BaseModel):
    success: bool
    output: str

    @model_serializer
    def ser_model(self) -> str:
        return self.output


class PythonCodeExecutionTool(BaseTool[CodeExecutionInput, CodeExecutionResult]):
    def __init__(self, executor: CodeExecutor):
        super().__init__(CodeExecutionInput, CodeExecutionResult, "CodeExecutor", "Execute Python code blocks.")
        self._executor = executor

    async def run(self, args: CodeExecutionInput, cancellation_token: CancellationToken) -> CodeExecutionResult:
        code_blocks = [CodeBlock(code=args.code, language="python")]
        future = asyncio.get_event_loop().run_in_executor(
            None, functools.partial(self._executor.execute_code_blocks, code_blocks=code_blocks)
        )
        cancellation_token.link_future(future)
        result = await future

        return CodeExecutionResult(success=result.exit_code == 0, output=result.output)
