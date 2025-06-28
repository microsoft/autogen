import asyncio
import builtins
from typing import Any, Dict, List, Literal, Mapping, Optional

from pydantic import BaseModel, Field
from typing_extensions import Self

from .._cancellation_token import CancellationToken
from .._component_config import Component, ComponentModel
from ._base import BaseTool, ToolSchema
from ._workbench import TextResultContent, ToolResult, Workbench


class ToolOverride(BaseModel):
    """Override configuration for a tool's name and/or description."""
    name: Optional[str] = None
    description: Optional[str] = None


class StaticWorkbenchConfig(BaseModel):
    tools: List[ComponentModel] = []
    tool_overrides: Dict[str, ToolOverride] = Field(default_factory=dict)


class StateicWorkbenchState(BaseModel):
    type: Literal["StaticWorkbenchState"] = "StaticWorkbenchState"
    tools: Dict[str, Mapping[str, Any]] = {}


class StaticWorkbench(Workbench, Component[StaticWorkbenchConfig]):
    """
    A workbench that provides a static set of tools that do not change after
    each tool execution.

    Args:
        tools (List[BaseTool[Any, Any]]): A list of tools to be included in the workbench.
            The tools should be subclasses of :class:`~autogen_core.tools.BaseTool`.
        tool_overrides (Optional[Dict[str, ToolOverride]]): Optional mapping of original tool
            names to override configurations for name and/or description. This allows
            customizing how tools appear to consumers while maintaining the underlying
            tool functionality.
    """

    component_provider_override = "autogen_core.tools.StaticWorkbench"
    component_config_schema = StaticWorkbenchConfig

    def __init__(
        self, 
        tools: List[BaseTool[Any, Any]], 
        tool_overrides: Optional[Dict[str, ToolOverride]] = None
    ) -> None:
        self._tools = tools
        self._tool_overrides = tool_overrides or {}
        
        # Build reverse mapping from override names to original names for call_tool
        self._override_name_to_original: Dict[str, str] = {}
        existing_tool_names = {tool.name for tool in self._tools}
        
        for original_name, override in self._tool_overrides.items():
            if override.name:
                # Check for conflicts with existing tool names
                if override.name in existing_tool_names and override.name != original_name:
                    raise ValueError(
                        f"Tool override name '{override.name}' conflicts with existing tool name. "
                        f"Override names must not conflict with any tool names."
                    )
                # Check for conflicts with other override names
                if override.name in self._override_name_to_original:
                    existing_original = self._override_name_to_original[override.name]
                    raise ValueError(
                        f"Tool override name '{override.name}' is used by multiple tools: "
                        f"'{existing_original}' and '{original_name}'. Override names must be unique."
                    )
                self._override_name_to_original[override.name] = original_name

    async def list_tools(self) -> List[ToolSchema]:
        result_schemas = []
        for tool in self._tools:
            original_schema = tool.schema
            
            # Apply overrides if they exist for this tool
            if tool.name in self._tool_overrides:
                override = self._tool_overrides[tool.name]
                # Create a new ToolSchema with overrides applied
                schema: ToolSchema = {
                    "name": override.name if override.name is not None else original_schema["name"],
                    "description": override.description if override.description is not None else original_schema.get("description", ""),
                }
                # Copy optional fields
                if "parameters" in original_schema:
                    schema["parameters"] = original_schema["parameters"]
                if "strict" in original_schema:
                    schema["strict"] = original_schema["strict"]
            else:
                schema = original_schema
            
            result_schemas.append(schema)
        return result_schemas

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        cancellation_token: CancellationToken | None = None,
        call_id: str | None = None,
    ) -> ToolResult:
        # Check if the name is an override name and map it back to the original
        original_name = self._override_name_to_original.get(name, name)
        
        tool = next((tool for tool in self._tools if tool.name == original_name), None)
        if tool is None:
            return ToolResult(
                name=name,  # Return the requested name (which might be overridden)
                result=[TextResultContent(content=f"Tool {name} not found.")],
                is_error=True,
            )
        if not cancellation_token:
            cancellation_token = CancellationToken()
        if not arguments:
            arguments = {}
        try:
            result_future = asyncio.ensure_future(tool.run_json(arguments, cancellation_token, call_id=call_id))
            cancellation_token.link_future(result_future)
            actual_tool_output = await result_future
            is_error = False
            result_str = tool.return_value_as_string(actual_tool_output)
        except Exception as e:
            result_str = self._format_errors(e)
            is_error = True
        return ToolResult(name=name, result=[TextResultContent(content=result_str)], is_error=is_error)

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def reset(self) -> None:
        return None

    async def save_state(self) -> Mapping[str, Any]:
        tool_states = StateicWorkbenchState()
        for tool in self._tools:
            tool_states.tools[tool.name] = await tool.save_state_json()
        return tool_states.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        parsed_state = StateicWorkbenchState.model_validate(state)
        for tool in self._tools:
            if tool.name in parsed_state.tools:
                await tool.load_state_json(parsed_state.tools[tool.name])

    def _to_config(self) -> StaticWorkbenchConfig:
        return StaticWorkbenchConfig(
            tools=[tool.dump_component() for tool in self._tools],
            tool_overrides=self._tool_overrides
        )

    @classmethod
    def _from_config(cls, config: StaticWorkbenchConfig) -> Self:
        return cls(
            tools=[BaseTool.load_component(tool) for tool in config.tools],
            tool_overrides=config.tool_overrides
        )

    def _format_errors(self, error: Exception) -> str:
        """Recursively format errors into a string."""

        error_message = ""
        if hasattr(builtins, "ExceptionGroup") and isinstance(error, builtins.ExceptionGroup):
            # ExceptionGroup is available in Python 3.11+.
            # TODO: how to make this compatible with Python 3.10?
            for sub_exception in error.exceptions:  # type: ignore
                error_message += self._format_errors(sub_exception)  # type: ignore
        else:
            error_message += f"{str(error)}\n"
        return error_message.strip()
