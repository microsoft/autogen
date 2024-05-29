from collections.abc import Sequence
from typing import Any, Callable, Dict, Protocol, TypedDict, Union, runtime_checkable

from typing_extensions import NotRequired, Required

from ..function_utils import get_function_schema
from ..types import FunctionDefinition


@runtime_checkable
class FunctionExecutor(Protocol):
    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str: ...

    @property
    def functions(self) -> Sequence[str]: ...


class FunctionInfo(TypedDict):
    func: Required[Callable[..., Any]]
    name: NotRequired[str]
    description: NotRequired[str]


def into_function_definition(
    func_info: Union[FunctionInfo, FunctionDefinition, Callable[..., Any]],
) -> FunctionDefinition:
    if isinstance(func_info, FunctionDefinition):
        return func_info
    elif isinstance(func_info, dict):
        name = func_info.get("name", func_info["func"].__name__)
        description = func_info.get("description", "")
        parameters = get_function_schema(func_info["func"], description="", name="")["function"]["parameters"]
        return FunctionDefinition(name=name, description=description, parameters=parameters)
    else:
        parameters = get_function_schema(func_info, description="", name="")["function"]["parameters"]
        return FunctionDefinition(name=func_info.__name__, description="", parameters=parameters)
