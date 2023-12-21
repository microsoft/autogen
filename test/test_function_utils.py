import inspect
from typing import Dict, List, Optional, Tuple, get_type_hints
from typing_extensions import Annotated

import pytest

from autogen.pydantic import PYDANTIC_V1, model_dump
from autogen.function_utils import (
    get_function_schema,
    get_parameter_json_schema,
    get_parameters,
    get_required_params,
    get_typed_signature,
    get_typed_annotation,
    get_typed_return_annotation,
)


def f(a: Annotated[str, "Parameter a"], b: int = 2, c: Annotated[float, "Parameter c"] = 0.1, *, d):
    pass


def g(
    a: Annotated[str, "Parameter a"],
    b: int = 2,
    c: Annotated[float, "Parameter c"] = 0.1,
    *,
    d: Dict[str, Tuple[Optional[int], List[float]]]
) -> str:
    pass


def test_get_typed_annotation() -> None:
    globalns = getattr(f, "__globals__", {})
    assert get_typed_annotation(str, globalns) == str
    assert get_typed_annotation("float", globalns) == float


def test_get_typed_signature() -> None:
    assert get_typed_signature(f).parameters == inspect.signature(f).parameters
    assert get_typed_signature(g).parameters == inspect.signature(g).parameters


def test_get_typed_return_annotation() -> None:
    assert get_typed_return_annotation(f) is None
    assert get_typed_return_annotation(g) == str


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
    typed_signature = get_typed_signature(f)
    param_annotations = {k: v.annotation for k, v in typed_signature.parameters.items()}
    param_annotations.pop("d")
    required = ["a", "c"]

    expected = {
        "type": "object",
        "properties": {
            "a": {"type": "string", "description": "Parameter a"},
            "b": {"type": "integer", "description": "b"},
            "c": {"type": "number", "description": "Parameter c"},
        },
        "required": ["a", "c"],
    }

    actual = model_dump(get_parameters(required, param_annotations))
    # actual = get_parameters(required, hints).model_dump()

    assert actual == expected, actual


async def a_g(
    a: Annotated[str, "Parameter a"],
    b: int = 2,
    c: Annotated[float, "Parameter c"] = 0.1,
    *,
    d: Dict[str, Tuple[Optional[int], List[float]]]
) -> str:
    pass


def test_get_function_schema_no_return_type() -> None:
    expected = (
        "The return type of a function must be annotated as either 'str', a subclass of "
        + "'pydantic.BaseModel' or an union of the previous ones."
    )

    with pytest.raises(TypeError) as e:
        get_function_schema(f, description="function g")

    assert str(e.value) == expected, str(e.value)


def test_get_function_schema() -> None:
    expected_v2 = {
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

    # the difference is that the v1 version does not handle Union types (Optional is Union[T, None])
    expected_v1 = {
        "description": "function g",
        "name": "fancy name for g",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "string", "description": "Parameter a"},
                "b": {"type": "integer", "description": "b"},
                "c": {"type": "number", "description": "Parameter c"},
                "d": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": [{"type": "integer"}, {"type": "array", "items": {"type": "number"}}],
                    },
                    "description": "d",
                },
            },
            "required": ["a", "d"],
        },
    }

    actual = get_function_schema(g, description="function g", name="fancy name for g")

    if PYDANTIC_V1:
        assert actual == expected_v1, actual
    else:
        assert actual == expected_v2, actual

    actual = get_function_schema(a_g, description="function g", name="fancy name for g")
    if PYDANTIC_V1:
        assert actual == expected_v1, actual
    else:
        assert actual == expected_v2, actual
