import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Dict, Generic, Mapping, Protocol, Type, TypedDict, TypeVar, cast, runtime_checkable

import jsonref
from pydantic import BaseModel
from typing_extensions import NotRequired

from ...base import CancellationToken
from .._function_utils import normalize_annotated_type

T = TypeVar("T", bound=BaseModel, contravariant=True)


class ParametersSchema(TypedDict):
    type: str
    properties: Dict[str, Any]
    required: NotRequired[Sequence[str]]


class ToolSchema(TypedDict):
    parameters: NotRequired[ParametersSchema]
    name: str
    description: NotRequired[str]


@runtime_checkable
class Tool(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def schema(self) -> ToolSchema: ...

    def args_type(self) -> Type[BaseModel]: ...

    def return_type(self) -> Type[Any]: ...

    def state_type(self) -> Type[BaseModel] | None: ...

    def return_value_as_string(self, value: Any) -> str: ...

    async def run_json(self, args: Mapping[str, Any], cancellation_token: CancellationToken) -> Any: ...

    def save_state_json(self) -> Mapping[str, Any]: ...

    def load_state_json(self, state: Mapping[str, Any]) -> None: ...


ArgsT = TypeVar("ArgsT", bound=BaseModel, contravariant=True)
ReturnT = TypeVar("ReturnT", bound=BaseModel, covariant=True)
StateT = TypeVar("StateT", bound=BaseModel)


class BaseTool(ABC, Tool, Generic[ArgsT, ReturnT]):
    def __init__(
        self,
        args_type: Type[ArgsT],
        return_type: Type[ReturnT],
        name: str,
        description: str,
    ) -> None:
        self._args_type = args_type
        # Normalize Annotated to the base type.
        self._return_type = normalize_annotated_type(return_type)
        self._name = name
        self._description = description

    @property
    def schema(self) -> ToolSchema:
        model_schema: Dict[str, Any] = self._args_type.model_json_schema()

        if "$defs" in model_schema:
            model_schema = cast(Dict[str, Any], jsonref.replace_refs(obj=model_schema, proxies=False))  # type: ignore
            del model_schema["$defs"]

        tool_schema = ToolSchema(
            name=self._name,
            description=self._description,
            parameters=ParametersSchema(
                type="object",
                properties=model_schema["properties"],
            ),
        )
        if "required" in model_schema:
            assert "parameters" in tool_schema
            tool_schema["parameters"]["required"] = model_schema["required"]

        return tool_schema

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def args_type(self) -> Type[BaseModel]:
        return self._args_type

    def return_type(self) -> Type[Any]:
        return self._return_type

    def state_type(self) -> Type[BaseModel] | None:
        return None

    def return_value_as_string(self, value: Any) -> str:
        if isinstance(value, BaseModel):
            dumped = value.model_dump()
            if isinstance(dumped, dict):
                return json.dumps(dumped)
            return str(dumped)

        return str(value)

    @abstractmethod
    async def run(self, args: ArgsT, cancellation_token: CancellationToken) -> ReturnT: ...

    async def run_json(self, args: Mapping[str, Any], cancellation_token: CancellationToken) -> Any:
        return_value = await self.run(self._args_type.model_validate(args), cancellation_token)
        return return_value

    def save_state_json(self) -> Mapping[str, Any]:
        return {}

    def load_state_json(self, state: Mapping[str, Any]) -> None:
        pass


class BaseToolWithState(BaseTool[ArgsT, ReturnT], ABC, Generic[ArgsT, ReturnT, StateT]):
    def __init__(
        self,
        args_type: Type[ArgsT],
        return_type: Type[ReturnT],
        state_type: Type[StateT],
        name: str,
        description: str,
    ) -> None:
        super().__init__(args_type, return_type, name, description)
        self._state_type = state_type

    @abstractmethod
    def save_state(self) -> StateT: ...

    @abstractmethod
    def load_state(self, state: StateT) -> None: ...

    def save_state_json(self) -> Mapping[str, Any]:
        return self.save_state().model_dump()

    def load_state_json(self, state: Mapping[str, Any]) -> None:
        self.load_state(self._state_type.model_validate(state))
