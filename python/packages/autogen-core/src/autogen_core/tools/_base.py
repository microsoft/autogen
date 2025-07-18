import json
import logging
import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Dict,
    Generic,
    Mapping,
    Optional,
    Protocol,
    Type,
    TypeVar,
    cast,
    runtime_checkable,
)

import jsonref
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import NotRequired, TypedDict

from .. import EVENT_LOGGER_NAME, CancellationToken
from .._component_config import ComponentBase
from .._function_utils import normalize_annotated_type
from .._telemetry import trace_tool_span
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


class ToolOverride(BaseModel):
    """Override configuration for a tool's name and/or description."""

    name: Optional[str] = None
    description: Optional[str] = None


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

    async def run_json(
        self, args: Mapping[str, Any], cancellation_token: CancellationToken, call_id: str | None = None
    ) -> Any: ...

    async def save_state_json(self) -> Mapping[str, Any]: ...

    async def load_state_json(self, state: Mapping[str, Any]) -> None: ...


@runtime_checkable
class StreamTool(Tool, Protocol):
    def run_json_stream(
        self, args: Mapping[str, Any], cancellation_token: CancellationToken, call_id: str | None = None
    ) -> AsyncGenerator[Any, None]: ...


ArgsT = TypeVar("ArgsT", bound=BaseModel, contravariant=True)
ReturnT = TypeVar("ReturnT", bound=BaseModel, covariant=True)
StateT = TypeVar("StateT", bound=BaseModel)
StreamT = TypeVar("StreamT", bound=BaseModel, covariant=True)


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

    async def run_json(
        self, args: Mapping[str, Any], cancellation_token: CancellationToken, call_id: str | None = None
    ) -> Any:
        """Run the tool with the provided arguments in a dictionary.

        Args:
            args (Mapping[str, Any]): The arguments to pass to the tool.
            cancellation_token (CancellationToken): A token to cancel the operation if needed.
            call_id (str | None): An optional identifier for the tool call, used for tracing.

        Returns:
            Any: The return value of the tool's run method.
        """
        with trace_tool_span(
            tool_name=self._name,
            tool_description=self._description,
            tool_call_id=call_id,
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


class BaseStreamTool(
    BaseTool[ArgsT, ReturnT], StreamTool, ABC, Generic[ArgsT, StreamT, ReturnT], ComponentBase[BaseModel]
):
    component_type = "tool"

    @abstractmethod
    def run_stream(self, args: ArgsT, cancellation_token: CancellationToken) -> AsyncGenerator[StreamT | ReturnT, None]:
        """Run the tool with the provided arguments and return a stream of data and end with the final return value."""
        ...

    async def run_json_stream(
        self,
        args: Mapping[str, Any],
        cancellation_token: CancellationToken,
        call_id: str | None = None,
    ) -> AsyncGenerator[StreamT | ReturnT, None]:
        """Run the tool with the provided arguments in a dictionary and return a stream of data
        from the tool's :meth:`run_stream` method and end with the final return value.

        Args:
            args (Mapping[str, Any]): The arguments to pass to the tool.
            cancellation_token (CancellationToken): A token to cancel the operation if needed.
            call_id (str | None): An optional identifier for the tool call, used for tracing.

        Returns:
            AsyncGenerator[StreamT | ReturnT, None]: A generator yielding results from the tool's :meth:`run_stream` method.
        """
        return_value: ReturnT | StreamT | None = None
        with trace_tool_span(
            tool_name=self._name,
            tool_description=self._description,
            tool_call_id=call_id,
        ):
            # Execute the tool's run_stream method
            async for result in self.run_stream(self._args_type.model_validate(args), cancellation_token):
                return_value = result
                yield result

        assert return_value is not None, "The tool must yield a final return value at the end of the stream."
        if not isinstance(return_value, self._return_type):
            raise TypeError(
                f"Expected return value of type {self._return_type.__name__}, but got {type(return_value).__name__}"
            )

        # Log the tool call event
        event = ToolCallEvent(
            tool_name=self.name,
            arguments=dict(args),  # Using the raw args passed to run_json
            result=self.return_value_as_string(return_value),
        )
        logger.info(event)


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


# Workbench host request/response interfaces
class BaseWorkbenchRequest(BaseModel):
    """Base class for all workbench requests to host agents."""

    model_config = ConfigDict(extra="allow")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class BaseWorkbenchResponse(BaseModel):
    """Base class for all responses from host agents."""

    model_config = ConfigDict(extra="allow")
    request_id: str
    error: str | None = None


class NoHostWorkbenchResponse(BaseWorkbenchResponse):
    error: str | None = "Workbench has no host bound to handle requests."


class ErrorWorkbenchResponse(BaseWorkbenchResponse): ...


@runtime_checkable
class WorkbenchHost(Protocol):
    """Protocol for objects that can handle workbench requests."""

    def handle_workbench_request(self, request: BaseWorkbenchRequest) -> Awaitable[BaseWorkbenchResponse]:
        """Handle a request from a workbench."""
        ...
