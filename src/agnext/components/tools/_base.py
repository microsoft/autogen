from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Mapping, Protocol, Type, TypeVar

from pydantic import BaseModel

from ...core import CancellationToken

T = TypeVar("T", bound=BaseModel, contravariant=True)


class Tool(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def schema(self) -> Mapping[str, Any]: ...

    def args_type(self) -> Type[BaseModel]: ...

    def return_type(self) -> Type[BaseModel]: ...

    def state_type(self) -> Type[BaseModel] | None: ...

    async def run_json(self, args: Mapping[str, Any], cancellation_token: CancellationToken) -> BaseModel: ...

    def save_state_json(self) -> Mapping[str, Any]: ...

    def load_state_json(self, state: Mapping[str, Any]) -> None: ...


ArgsT = TypeVar("ArgsT", bound=BaseModel, contravariant=True)
ReturnT = TypeVar("ReturnT", bound=BaseModel, covariant=True)
StateT = TypeVar("StateT", bound=BaseModel)


class BaseTool(ABC, Tool, Generic[ArgsT, ReturnT]):
    def __init__(self, args_type: Type[ArgsT], return_type: Type[ReturnT], name: str, description: str) -> None:
        self._args_type = args_type
        self._return_type = return_type
        self._name = name
        self._description = description

    @property
    def schema(self) -> Mapping[str, Any]:
        model_schema = self._args_type.model_json_schema()
        parameter_schema: Dict[str, Any] = dict()
        parameter_schema["parameters"] = model_schema["properties"]
        parameter_schema["name"] = self._name
        parameter_schema["description"] = self._description
        return parameter_schema

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def args_type(self) -> Type[BaseModel]:
        return self._args_type

    def return_type(self) -> Type[BaseModel]:
        return self._return_type

    def state_type(self) -> Type[BaseModel] | None:
        return None

    @abstractmethod
    async def run(self, args: ArgsT, cancellation_token: CancellationToken) -> ReturnT: ...

    async def run_json(self, args: Mapping[str, Any], cancellation_token: CancellationToken) -> BaseModel:
        return_value = await self.run(self._args_type.model_validate(args), cancellation_token)
        return return_value

    def save_state_json(self) -> Mapping[str, Any]:
        return {}

    def load_state_json(self, state: Mapping[str, Any]) -> None:
        pass


class BaseToolWithState(BaseTool[ArgsT, ReturnT], ABC, Generic[ArgsT, ReturnT, StateT]):
    def __init__(
        self, args_type: Type[ArgsT], return_type: Type[ReturnT], state_type: Type[StateT], name: str, description: str
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
