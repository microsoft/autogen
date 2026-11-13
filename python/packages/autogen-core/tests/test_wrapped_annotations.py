from datetime import datetime
from functools import wraps
from types import ModuleType
from typing import Any, Callable

import pytest
from autogen_core import CancellationToken
from autogen_core._function_utils import get_function_schema, get_typed_return_annotation, get_typed_signature
from autogen_core.tools import FunctionTool


@pytest.fixture(params=[0, 1, 2])
def wrapped_function(request: pytest.FixtureRequest) -> Callable[..., Any]:
    module = ModuleType("wrapped_tool_module")
    exec(
        "from datetime import datetime as Timestamp\n"
        "def echo(value: 'Timestamp') -> 'Timestamp':\n"
        "    return value\n",
        module.__dict__,
    )

    def decorate(original: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(original)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return original(*args, **kwargs)

        return wrapper

    function: Callable[..., Any] = module.echo
    for _ in range(request.param):
        function = decorate(function)
    return function


def test_wrapped_function_signature(wrapped_function: Callable[..., Any]) -> None:
    signature = get_typed_signature(wrapped_function)
    assert signature.parameters["value"].annotation is datetime
    assert signature.return_annotation is datetime


def test_wrapped_function_return_annotation(wrapped_function: Callable[..., Any]) -> None:
    assert get_typed_return_annotation(wrapped_function) is datetime


def test_wrapped_function_schema(wrapped_function: Callable[..., Any]) -> None:
    schema = get_function_schema(wrapped_function, description="Echo a timestamp.")
    assert schema["function"]["parameters"]["properties"]["value"]["format"] == "date-time"


@pytest.mark.asyncio
async def test_wrapped_function_tool(wrapped_function: Callable[..., Any]) -> None:
    tool = FunctionTool(wrapped_function, description="Echo a timestamp.")
    schema = tool.schema
    assert "parameters" in schema
    assert schema["parameters"]["properties"]["value"]["format"] == "date-time"
    assert tool.return_type() is datetime
    assert await tool.run_json({"value": "2026-10-05T12:00:00"}, CancellationToken()) == datetime(2026, 10, 5, 12)
