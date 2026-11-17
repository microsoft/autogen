import functools

from autogen_core._function_utils import get_typed_return_annotation


def annotated(a: int) -> str:
    return str(a)


def unannotated(a: int):
    return a


def test_partial_return_annotation_uses_the_wrapped_function() -> None:
    # Used to raise TypeError: functools.partial(...) is not a module, class,
    # method, or function.
    assert get_typed_return_annotation(functools.partial(annotated, 1)) is str


def test_partial_without_return_annotation_returns_none() -> None:
    assert get_typed_return_annotation(functools.partial(unannotated, 1)) is None


def test_plain_function_return_annotation_unchanged() -> None:
    assert get_typed_return_annotation(annotated) is str
    assert get_typed_return_annotation(unannotated) is None
