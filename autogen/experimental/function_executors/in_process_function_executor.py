import asyncio
import functools
from typing import Any, Callable, Dict, List, Union
from autogen.experimental.agents.assistant_agent import FunctionInfo
from autogen.experimental.function_executor import FunctionExecutor


class InProcessFunctionExecutor(FunctionExecutor):
    def __init__(
        self,
        functions: List[Union[Callable[..., Any], FunctionInfo]] = [],
    ) -> None:
        def _name(func: Union[Callable[..., Any], FunctionInfo]) -> str:
            if isinstance(func, dict):
                return func.get("name", func.get("func").__name__)
            else:
                return func.__name__

        def _func(func: Union[Callable[..., Any], FunctionInfo]) -> Any:
            if isinstance(func, dict):
                return func.get("func")
            else:
                return func

        self._functions = dict([(_name(x), _func(x)) for x in functions])

    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        if function_name in self._functions:
            function = self._functions[function_name]
            if asyncio.iscoroutinefunction(function):
                return str(function(**arguments))
            else:
                return await asyncio.get_event_loop().run_in_executor(None, functools.partial(function, **arguments))

        raise ValueError(f"Function {function_name} not found")

    @property
    def functions(self) -> List[str]:
        return list(self._functions.keys())
