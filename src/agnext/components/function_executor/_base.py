from collections.abc import Sequence
from typing import Any, Callable, Dict, Protocol, TypedDict, Union, runtime_checkable

from typing_extensions import NotRequired, Required

from ..function_utils import get_function_schema
from ..types import FunctionSignature


class Function(TypedDict):
    func: Required[Callable[..., Any]]
    name: NotRequired[str]
    description: NotRequired[str]


@runtime_checkable
class FunctionExecutor(Protocol):
    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str: ...

    @property
    def functions(self) -> Sequence[Function]: ...

    @property
    def function_signatures(self) -> Sequence[FunctionSignature]:
        return [into_function_signature(func) for func in self.functions]


def into_function_signature(
    func_data: Union[Function, FunctionSignature, Callable[..., Any]],
) -> FunctionSignature:
    if isinstance(func_data, FunctionSignature):
        return func_data
    elif isinstance(func_data, dict):
        name = func_data.get("name", func_data["func"].__name__)
        description = func_data.get("description", "")
        parameters = get_function_schema(func_data["func"], description="", name="")["function"]["parameters"]
        return FunctionSignature(name=name, description=description, parameters=parameters)
    else:
        parameters = get_function_schema(func_data, description="", name="")["function"]["parameters"]
        return FunctionSignature(name=func_data.__name__, description="", parameters=parameters)
