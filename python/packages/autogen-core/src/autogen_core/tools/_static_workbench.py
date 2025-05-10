import asyncio
from typing import Any, Dict, List, Literal, Mapping

from pydantic import BaseModel
from typing_extensions import Self
import builtins


from .._cancellation_token import CancellationToken
from .._component_config import Component, ComponentModel
from ._base import BaseTool, ToolSchema
from ._workbench import TextResultContent, ToolResult, Workbench


class StaticWorkbenchConfig(BaseModel):
    tools: List[ComponentModel] = []


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
    """

    component_provider_override = "autogen_core.tools.StaticWorkbench"
    component_config_schema = StaticWorkbenchConfig

    def __init__(self, tools: List[BaseTool[Any, Any]]) -> None:
        self._tools = tools

    async def list_tools(self) -> List[ToolSchema]:
        return [tool.schema for tool in self._tools]

    async def call_tool(
        self, name: str, arguments: Mapping[str, Any] | None = None, cancellation_token: CancellationToken | None = None
    ) -> ToolResult:
        tool = next((tool for tool in self._tools if tool.name == name), None)
        if tool is None:
            return ToolResult(
                name=name,
                result=[TextResultContent(content=f"Tool {name} not found.")],
                is_error=True,
            )
        if not cancellation_token:
            cancellation_token = CancellationToken()
        if not arguments:
            arguments = {}
        try:
            result_future = asyncio.ensure_future(tool.run_json(arguments, cancellation_token))
            cancellation_token.link_future(result_future)
            actual_tool_output = await result_future
            is_error = False
            result_str = tool.return_value_as_string(actual_tool_output)
        except Exception as e:
            result_str = self._format_errors(e)
            is_error = True
        return ToolResult(name=tool.name, result=[TextResultContent(content=result_str)], is_error=is_error)

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
        return StaticWorkbenchConfig(tools=[tool.dump_component() for tool in self._tools])

    @classmethod
    def _from_config(cls, config: StaticWorkbenchConfig) -> Self:
        return cls(tools=[BaseTool.load_component(tool) for tool in config.tools])

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
