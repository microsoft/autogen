import inspect

import pytest

from autogen_core._function_utils import get_function_schema, get_typed_signature


def unannotated_parameter(a: int, b):
    return a


def fully_annotated(a: int, b: str = "x") -> str:
    return str(a) + b


def test_unannotated_parameter_raises_the_documented_type_error() -> None:
    # Used to raise KeyError: 'b' before the explanatory TypeError.
    with pytest.raises(TypeError, match="must be annotated"):
        get_function_schema(unannotated_parameter, description="d")


def test_unannotated_parameter_is_kept_as_empty_annotation() -> None:
    signature = get_typed_signature(unannotated_parameter)

    assert signature.parameters["a"].annotation is int
    assert signature.parameters["b"].annotation is inspect.Signature.empty


def test_fully_annotated_function_still_builds_a_schema() -> None:
    schema = get_function_schema(fully_annotated, description="d")

    assert schema["function"]["parameters"]["required"] == ["a"]
