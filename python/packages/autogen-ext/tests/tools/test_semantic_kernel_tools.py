from typing import Any, Dict

from autogen_core.tools import ToolSchema

from autogen_ext.tools.semantic_kernel import KernelFunctionFromTool, KernelFunctionFromToolSchema


def _required_flags(schema: ToolSchema) -> Dict[str, bool]:
    """Build a mapping of parameter name to required flag from the schema-derived kernel function."""
    function = KernelFunctionFromToolSchema(schema)
    return {param.name: bool(param.is_required) for param in function.metadata.parameters}


def test_kernel_function_from_tool_schema_marks_required_parameters() -> None:
    """Parameters listed in the tool schema's `required` array must be marked as required."""
    schema: ToolSchema = {
        "type": "function",
        "name": "lookup",
        "description": "Look up a value",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The thing to look up"},
                "limit": {"type": "integer", "description": "Optional cap on the number of results"},
            },
            "required": ["query"],
        },
    }

    flags = _required_flags(schema)

    assert flags["query"] is True
    assert flags["limit"] is False


def test_kernel_function_from_tool_schema_without_required() -> None:
    """Schemas without a `required` array leave every parameter optional."""
    schema: ToolSchema = {
        "type": "function",
        "name": "ping",
        "description": "Ping a host",
        "parameters": {
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "The host to ping"},
            },
        },
    }

    flags = _required_flags(schema)

    assert flags["host"] is False


def test_kernel_function_from_tool_marks_required_parameters() -> None:
    """Control: the BaseTool path already reports required parameters correctly."""
    from typing import Optional

    from autogen_core import CancellationToken
    from autogen_core.tools import BaseTool
    from pydantic import BaseModel

    class LookupArgs(BaseModel):
        query: str
        limit: Optional[int] = None

    class LookupResult(BaseModel):
        answer: str

    class LookupTool(BaseTool[LookupArgs, LookupResult]):
        def __init__(self) -> None:
            super().__init__(args_type=LookupArgs, return_type=LookupResult, name="lookup", description="Look up")

        async def run(self, args: LookupArgs, cancellation_token: CancellationToken) -> LookupResult:
            return LookupResult(answer="answer")

    function = KernelFunctionFromTool(LookupTool())
    flags = {param.name: bool(param.is_required) for param in function.metadata.parameters}

    assert flags["query"] is True
    assert flags["limit"] is False
