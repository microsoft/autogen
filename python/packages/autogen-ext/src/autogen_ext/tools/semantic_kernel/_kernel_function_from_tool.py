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
    """
    KernelFunctionFromTool is an adapter that allows using Autogen tools as Semantic Kernel functions.
    This makes it possible to integrate Autogen tools into Semantic Kernel when using the Semantic Kernel's
    chat completion adapter or agent.

    By leveraging this adapter, you can:
        - Convert any Autogen BaseTool into a Semantic Kernel KernelFunction
        - Register the converted tool with a Semantic Kernel plugin
        - Execute the tool through Semantic Kernel's function invocation mechanism
        - Access tool metadata (name, description, parameters) through Semantic Kernel's metadata system

    Args:
        tool (BaseTool[InputT, OutputT]):
            The Autogen tool to wrap. Must be a subclass of BaseTool with Pydantic models for input/output.
        plugin_name (str | None):
            Optional name of the plugin this function belongs to. Defaults to None.

    Example usage:
        .. code-block:: python

            from pydantic import BaseModel
            from autogen_core.tools import BaseTool
            from autogen_core import CancellationToken
            from autogen_ext.tools.semantic_kernel import KernelFunctionFromTool
            from semantic_kernel.functions.kernel_plugin import KernelPlugin
            from semantic_kernel.kernel import Kernel


            # 1) Define input/output models
            class CalculatorArgs(BaseModel):
                a: float
                b: float


            class CalculatorResult(BaseModel):
                result: float


            # 2) Create an Autogen tool
            class CalculatorTool(BaseTool[CalculatorArgs, CalculatorResult]):
                def __init__(self) -> None:
                    super().__init__(
                        args_type=CalculatorArgs,
                        return_type=CalculatorResult,
                        name="calculator",
                        description="Add two numbers together",
                    )

                async def run(self, args: CalculatorArgs, cancellation_token: CancellationToken) -> CalculatorResult:
                    return CalculatorResult(result=args.a + args.b)


            # 3) Convert to Semantic Kernel function
            calc_tool = CalculatorTool()
            kernel_function = KernelFunctionFromTool(calc_tool, plugin_name="math")

            # 4) Add to Semantic Kernel plugin/kernel
            plugin = KernelPlugin(name="math")
            plugin.functions[calc_tool.name] = kernel_function
            kernel = Kernel()
            kernel.add_plugin(plugin)
    """

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

        # Call your tool's run_json
        result = await self._tool.run_json(tool_args, cancellation_token=CancellationToken())

        # Wrap in a FunctionResult
        context.result = FunctionResult(
            function=self.metadata,
            value=result,
            metadata={"used_arguments": tool_args},
        )

    async def _invoke_internal_stream(self, context: FunctionInvocationContext) -> None:
        # If you don't have a streaming mechanism in your tool, you can simply reuse _invoke_internal
        # or raise NotImplementedError. For example:
        await self._invoke_internal(context)
