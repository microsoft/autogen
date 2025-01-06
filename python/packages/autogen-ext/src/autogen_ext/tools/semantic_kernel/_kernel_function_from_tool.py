from typing import TypeVar

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from pydantic import BaseModel
from semantic_kernel.exceptions import FunctionExecutionException
from semantic_kernel.filters.functions.function_invocation_context import FunctionInvocationContext
from semantic_kernel.functions.function_result import FunctionResult
from semantic_kernel.functions.kernel_function import KernelFunction
from semantic_kernel.functions.kernel_function_metadata import KernelFunctionMetadata
from semantic_kernel.functions.kernel_parameter_metadata import KernelParameterMetadata

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class KernelFunctionFromTool(KernelFunction):
    def __init__(self, tool: BaseTool[InputT, OutputT], plugin_name: str | None = None):
        # Build up KernelFunctionMetadata. You can also parse the tool's schema for parameters.
        parameters = [
            KernelParameterMetadata(
                name="args",
                description="JSON arguments for the tool",
                default_value=None,
                type="dict",
                type_object=dict,
                is_required=True,
            )
        ]
        return_param = KernelParameterMetadata(
            name="return",
            description="Result from the tool",
            default_value=None,
            type="str",
            type_object=str,
            is_required=False,
        )

        metadata = KernelFunctionMetadata(
            name=tool.name,
            description=tool.description,
            parameters=parameters,
            return_parameter=return_param,
            is_prompt=False,
            is_asynchronous=True,
            plugin_name=plugin_name or "",
        )
        super().__init__(metadata=metadata)
        self._tool = tool

    async def _invoke_internal(self, context: FunctionInvocationContext) -> None:
        # Extract the "args" parameter from the context
        if "args" not in context.arguments:
            raise FunctionExecutionException("Missing 'args' in FunctionInvocationContext.arguments")
        tool_args = context.arguments

        # Call your tool’s run_json
        result = await self._tool.run_json(tool_args, cancellation_token=CancellationToken())

        # Wrap in a FunctionResult
        context.result = FunctionResult(
            function=self.metadata,
            value=result,
            metadata={"used_arguments": tool_args},
        )

    async def _invoke_internal_stream(self, context: FunctionInvocationContext) -> None:
        # If you don’t have a streaming mechanism in your tool, you can simply reuse _invoke_internal
        # or raise NotImplementedError. For example:
        await self._invoke_internal(context)
