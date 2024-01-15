import pytest
from autogen.middleware.conditions import Always, IsInstance, Never, Condition


def test_always() -> None:
    cond = Condition.true()
    assert isinstance(cond, Always)
    assert cond("whatever") is True


def test_never() -> None:
    cond = Condition.false()
    assert isinstance(cond, Never)
    assert cond("whatever") is False


def test_isinstance() -> None:
    class A:
        pass

    a = A()

    cond = Condition.isinstance(A)
    assert cond(a)
    assert not cond(int)
