from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class FunctionExecutor(Protocol):
    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str: ...

    @property
    def functions(self) -> List[str]: ...
