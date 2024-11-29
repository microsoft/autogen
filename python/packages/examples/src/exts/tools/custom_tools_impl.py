import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Dict, Generic, Mapping, Protocol, Type, TypedDict, TypeVar, runtime_checkable

from autogen_core.base import CancellationToken
from pydantic import BaseModel
from typing_extensions import NotRequired
from autogen_core.components.tools import FunctionTool
from autogen_core.components.tools import Tool, ToolSchema,ParametersSchema

class JsonSchemaTool(Tool):
    def __init__(
        self,
        tool_schema: ToolSchema,
        name: str,
        description: str,
    ) -> None:
        self._tool_schema = tool_schema
        # Normalize Annotated to the base type.
        self._name = name
        self._description = description

    @property
    def schema(self) -> ToolSchema:
        return self._tool_schema

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def args_type(self) -> Type[BaseModel]:
        pass

    def return_type(self) -> Type[Any]:
        pass

    def state_type(self) -> Type[BaseModel] | None:
        pass

    def return_value_as_string(self, value: Any) -> str:
        if isinstance(value, BaseModel):
            dumped = value.model_dump()
            if isinstance(dumped, dict):
                return json.dumps(dumped)
            return str(dumped)

        return str(value)

    async def run(self, args: Any, cancellation_token: CancellationToken) -> str: 
        print(f"工具参数是：{args}")

    async def run_json(self, args: Mapping[str, Any], cancellation_token: CancellationToken) -> Any:
        return_value = await self.run(self._args_type.model_validate(args), cancellation_token)
        return return_value

    def save_state_json(self) -> Mapping[str, Any]:
        return {}

    def load_state_json(self, state: Mapping[str, Any]) -> None:
        pass