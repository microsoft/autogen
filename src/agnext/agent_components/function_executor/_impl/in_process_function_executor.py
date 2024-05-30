import asyncio
import functools
from collections.abc import Sequence
from typing import Any, Callable, Dict, Union

from .._base import Function, FunctionExecutor


class InProcessFunctionExecutor(FunctionExecutor):
    def __init__(
        self,
        functions: Sequence[Union[Callable[..., Any], Function]] = [],
    ) -> None:
        def _name(func: Union[Callable[..., Any], Function]) -> str:
            if isinstance(func, dict):
                return func.get("name", func["func"].__name__)
            else:
                return func.__name__

        def _func(func: Union[Callable[..., Any], Function]) -> Any:
            if isinstance(func, dict):
                return func.get("func")
            else:
                return func

        def _description(func: Union[Callable[..., Any], Function]) -> str:
            if isinstance(func, dict):
                return func.get("description", "")
            else:
                return ""

        self._functions: Dict[str, Function] = dict()
        for func in functions:
            name = _name(func)
            self._functions[name] = Function(
                func=_func(func),
                name=name,
                description=_description(func),
            )

    async def execute_function(self, function_name: str, arguments: dict[str, Any]) -> str:
        if function_name in self._functions:
            function = self._functions[function_name]["func"]
            if asyncio.iscoroutinefunction(function):
                return str(function(**arguments))
            else:
                return await asyncio.get_event_loop().run_in_executor(None, functools.partial(function, **arguments))

        raise ValueError(f"Function {function_name} not found.")

    @property
    def functions(self) -> Sequence[Function]:
        return list(self._functions.values())
