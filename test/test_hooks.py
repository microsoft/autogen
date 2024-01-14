import pytest
from autogen.hooks import hookable_method, hookable_function


def test_hookable_method() -> None:
    class A:
        @hookable_method
        def f(self, x: float, y: float, *, z: int) -> float:
            return (x + y) * z

    a = A()

    # we can add hooks using decorators
    @a.f.add_pre_hook
    def add_one(x: float, y: float, *, z: int) -> float:
        return x + 1

    with pytest.raises(ValueError) as e:
        a.f.add_pre_hook(add_one)

    assert str(e.value).endswith("is already registered.")

    def deduct_one(x: float, y: float, *, z: int) -> float:
        return x - 1

    # or we can add hooks using function calls
    a.f.add_post_hook(deduct_one)

    with pytest.raises(ValueError) as e:
        a.f.add_post_hook(add_one)

    assert str(e.value).endswith("is already registered.")

    assert a.f(1.1, 2.2, z=3) == (1.1 + 1 + 2.2) * 3 - 1


def test_hookable_function() -> None:
    @hookable_function
    def g(x: float, y: float, *, z: int) -> float:
        return (x + y) * z

    # we can add hooks using decorators
    @g.add_pre_hook
    def add_one(x: float, y: float, *, z: int) -> float:
        return x + 1

    def deduct_one(x: float, y: float, *, z: int) -> float:
        return x - 1

    # or we can add hooks using function calls
    g.add_post_hook(deduct_one)

    assert g(1.1, 2.2, z=3) == (1.1 + 1 + 2.2) * 3 - 1
