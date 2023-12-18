import inspect
from typing import Dict, List, Optional, Tuple, get_type_hints

from typing_extensions import Annotated

from autogen.function_utils import (
    get_function_schema,
    get_parameter_json_schema,
    get_parameters,
    get_required_params,
)


def f(a: Annotated[str, "Parameter a"], b: int = 2, c: Annotated[float, "Parameter c"] = 0.1, *, d):
    pass


def test_get_parameter_json_schema() -> None:
    assert get_parameter_json_schema("a", Annotated[str, "parameter a"]) == {
        "type": "string",
        "description": "parameter a",
    }
    assert get_parameter_json_schema("b", str) == {"type": "string", "description": "b"}


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
            "b": {"type": "integer", "description": "b"},
            "c": {"type": "number", "description": "Parameter c"},
        },
        "required": ["a", "d"],
    }

    actual = get_parameters(required, hints).model_dump()

    assert actual == expected, actual


def g(
    a: Annotated[str, "Parameter a"],
    b: int = 2,
    c: Annotated[float, "Parameter c"] = 0.1,
    *,
    d: Dict[str, Tuple[Optional[int], List[float]]]
) -> str:
    pass


def test_get_function() -> None:
    expected = {
        "description": "function g",
        "name": "fancy name for g",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "string", "description": "Parameter a"},
                "b": {"type": "integer", "description": "b"},
                "c": {"type": "number", "description": "Parameter c"},
                "d": {
                    "additionalProperties": {
                        "maxItems": 2,
                        "minItems": 2,
                        "prefixItems": [
                            {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                            {"items": {"type": "number"}, "type": "array"},
                        ],
                        "type": "array",
                    },
                    "type": "object",
                    "description": "d",
                },
            },
            "required": ["a", "d"],
        },
    }

    actual = get_function_schema(g, description="function g", name="fancy name for g")

    assert actual == expected, actual
