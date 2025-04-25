import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Dict, Generic, Mapping, Protocol, Type, TypeVar, cast, runtime_checkable

import jsonref
from opentelemetry.trace import get_tracer
from pydantic import BaseModel
from typing_extensions import NotRequired, TypedDict

from .. import EVENT_LOGGER_NAME, CancellationToken
from .._component_config import ComponentBase
from .._function_utils import normalize_annotated_type
from ..logging import ToolCallEvent

T = TypeVar("T", bound=BaseModel, contravariant=True)

logger = logging.getLogger(EVENT_LOGGER_NAME)


class ParametersSchema(TypedDict):
    type: str
    properties: Dict[str, Any]
    required: NotRequired[Sequence[str]]
    additionalProperties: NotRequired[bool]


class ToolSchema(TypedDict):
    parameters: NotRequired[ParametersSchema]
    name: str
    description: NotRequired[str]
    strict: NotRequired[bool]


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

    async def save_state_json(self) -> Mapping[str, Any]: ...

    async def load_state_json(self, state: Mapping[str, Any]) -> None: ...


ArgsT = TypeVar("ArgsT", bound=BaseModel, contravariant=True)
ReturnT = TypeVar("ReturnT", bound=BaseModel, covariant=True)
StateT = TypeVar("StateT", bound=BaseModel)


class BaseTool(ABC, Tool, Generic[ArgsT, ReturnT], ComponentBase[BaseModel]):
    component_type = "tool"

    def __init__(
        self,
        args_type: Type[ArgsT],
        return_type: Type[ReturnT],
        name: str,
        description: str,
        strict: bool = False,
    ) -> None:
        self._args_type = args_type
        # Normalize Annotated to the base type.
        self._return_type = normalize_annotated_type(return_type)
        self._name = name
        self._description = description
        self._strict = strict

    @property
    def schema(self) -> ToolSchema:
        model_schema: Dict[str, Any] = self._args_type.model_json_schema()

        if "$defs" in model_schema:
            model_schema = cast(Dict[str, Any], jsonref.replace_refs(obj=model_schema, proxies=False))  # type: ignore
            del model_schema["$defs"]

        parameters = ParametersSchema(
            type="object",
            properties=model_schema["properties"],
            required=model_schema.get("required", []),
            additionalProperties=model_schema.get("additionalProperties", False),
        )

        # If strict is enabled, the tool schema should list all properties as required.
        assert "required" in parameters
        if self._strict and set(parameters["required"]) != set(parameters["properties"].keys()):
            raise ValueError(
                "Strict mode is enabled, but not all input arguments are marked as required. Default arguments are not allowed in strict mode."
            )

        assert "additionalProperties" in parameters
        if self._strict and parameters["additionalProperties"]:
            raise ValueError(
                "Strict mode is enabled but additional argument is also enabled. This is not allowed in strict mode."
            )

        tool_schema = ToolSchema(
            name=self._name,
            description=self._description,
            parameters=parameters,
            strict=self._strict,
        )
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
        with get_tracer("base_tool").start_as_current_span(
            self._name,
            attributes={
                "tool_name": self._name,
                "tool_description": self._description,
                "tool_args": json.dumps(args),
            },
        ):
            # Execute the tool's run method
            return_value = await self.run(self._args_type.model_validate(args), cancellation_token)

        # Log the tool call event
        event = ToolCallEvent(
            tool_name=self.name,
            arguments=dict(args),  # Using the raw args passed to run_json
            result=self.return_value_as_string(return_value),
        )
        logger.info(event)

        return return_value

    async def save_state_json(self) -> Mapping[str, Any]:
        return {}

    async def load_state_json(self, state: Mapping[str, Any]) -> None:
        pass


class BaseToolWithState(BaseTool[ArgsT, ReturnT], ABC, Generic[ArgsT, ReturnT, StateT], ComponentBase[BaseModel]):
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

    component_type = "tool"

    @abstractmethod
    def save_state(self) -> StateT: ...

    @abstractmethod
    def load_state(self, state: StateT) -> None: ...

    async def save_state_json(self) -> Mapping[str, Any]:
        return self.save_state().model_dump()

    async def load_state_json(self, state: Mapping[str, Any]) -> None:
        self.load_state(self._state_type.model_validate(state))
