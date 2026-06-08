from typing import Any, TypeVar

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool, ToolSchema
from pydantic import BaseModel

from semantic_kernel.functions import KernelFunctionFromMethod, KernelFunctionFromPrompt, kernel_function
from semantic_kernel.functions.kernel_parameter_metadata import KernelParameterMetadata
from semantic_kernel.prompt_template.input_variable import InputVariable
from semantic_kernel.prompt_template.prompt_template_config import PromptTemplateConfig

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class KernelFunctionFromTool(KernelFunctionFromMethod):
    def __init__(self, tool: BaseTool[InputT, OutputT], plugin_name: str | None = None):
        # Get the pydantic model types from the tool
        args_type = tool.args_type()
        return_type = tool.return_type()

        # 1) Define an async function that calls the tool
        @kernel_function(name=tool.name, description=tool.description)
        async def tool_method(**kwargs: dict[str, Any]) -> Any:
            return await tool.run_json(kwargs, cancellation_token=CancellationToken())

        # Parse schema for parameters
        parameters_meta: list[KernelParameterMetadata] = []
        properties = tool.schema.get("parameters", {}).get("properties", {})

        # Get the field types from the pydantic model
        field_types = args_type.model_fields

        for prop_name, prop_info in properties.items():
            assert prop_name in field_types, f"Property {prop_name} not found in Tool {tool.name}"
            assert isinstance(prop_info, dict), f"Property {prop_name} is not a dict in Tool {tool.name}"

            # Get the actual type from the pydantic model field
            field_type = field_types[prop_name]
            parameters_meta.append(
                KernelParameterMetadata(
                    name=prop_name,
                    description=field_type.description or "",
                    default_value=field_type.get_default(),
                    type=prop_info.get("type", "string"),  # type: ignore
                    type_object=field_type.annotation,
                    is_required=field_type.is_required(),
                )
            )

        # Create return parameter metadata
        return_parameter = KernelParameterMetadata(
            name="return",
            description=f"Result from '{tool.name}' tool",
            default_value=None,
            type="object" if issubclass(return_type, BaseModel) else "string",
            type_object=return_type,
            is_required=True,
        )

        # Initialize the parent class
        super().__init__(
            method=tool_method,
            plugin_name=plugin_name,
            parameters=parameters_meta,
            return_parameter=return_parameter,
            additional_metadata=None,
        )

        self._tool = tool


class KernelFunctionFromToolSchema(KernelFunctionFromPrompt):
    def __init__(self, tool_schema: ToolSchema, plugin_name: str | None = None):
        properties = tool_schema.get("parameters", {}).get("properties", {})
        required = properties.get("required", [])

        prompt_template_config = PromptTemplateConfig(
            name=tool_schema.get("name", ""),
            description=tool_schema.get("description", ""),
            input_variables=[
                InputVariable(
                    name=prop_name, description=prop_info.get("description", ""), is_required=prop_name in required
                )
                for prop_name, prop_info in properties.items()
            ],
        )

        super().__init__(
            function_name=tool_schema.get("name", ""),
            plugin_name=plugin_name,
            description=tool_schema.get("description", ""),
            prompt_template_config=prompt_template_config,
        )
