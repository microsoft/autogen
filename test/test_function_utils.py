import inspect

from typing import get_type_hints
import pytest
from typing_extensions import Annotated

from autogen.function_utils import Parameter, get_parameter, get_required_params, get_parameters, get_function


def f(a: Annotated[str, "Parameter a"], b: int = 2, c: Annotated[float, "Parameter c"] = 0.1, *, d):
    pass


def g(a: Annotated[str, "Parameter a"], b: int = 2, c: Annotated[float, "Parameter c"] = 0.1, *, d: str) -> str:
    pass


def test_get_parameter() -> None:
    assert get_parameter("a", Annotated[str, "parameter a"]) == Parameter(type="string", description="parameter a")
    assert get_parameter("b", str) == Parameter(type="string", description="b"), get_parameter("b", str)


def test_get_required_params() -> None:
    assert get_required_params(inspect.signature(f)) == ["a", "d"]
    assert get_required_params(inspect.signature(g)) == ["a", "d"]


def test_get_parameters() -> None:
    hints = get_type_hints(f, include_extras=True)
    signature = inspect.signature(f)
    required = get_required_params(signature)

    expected = {
        "type": "object",
        "properties": {
            "a": {"type": "string", "description": "Parameter a"},
            "b": {"type": "int", "description": "b"},
            "c": {"type": "float", "description": "Parameter c"},
        },
        "required": ["a", "d"],
    }

    actual = get_parameters(required, hints).model_dump()

    assert actual == expected, actual


def test_get_function() -> None:
    expected = {
        "description": "function g",
        "name": "fancy name for g",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "string", "description": "Parameter a"},
                "b": {"type": "int", "description": "b"},
                "c": {"type": "float", "description": "Parameter c"},
                "d": {"type": "string", "description": "d"},
            },
            "required": ["a", "d"],
        },
    }

    actual = get_function(g, description="function g", name="fancy name for g")

    assert actual == expected, actual
