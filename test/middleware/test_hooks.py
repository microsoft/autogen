from unittest.mock import MagicMock, AsyncMock
import pytest
from autogen.middleware.conditions import Condition
from autogen.middleware.hooks import await_if_needed, hookable_method, hookable_function

from ..mocks import monitor_calls


@pytest.mark.asyncio()
async def test_await_if_needed() -> None:
    assert await await_if_needed(1) == 1

    async def f() -> int:
        return 2

    assert await await_if_needed(f()) == 2


@pytest.mark.parametrize("cond", [None, Condition.true()])
def test_hookable_method_sync(cond: Condition) -> None:
    f_mock = MagicMock()
    add_one_mock = MagicMock()
    deduct_one_mock = MagicMock()

    class A:
        @hookable_method(cond=cond)
        @monitor_calls(f_mock)
        def f(self, x: float, y: float, *, z: int) -> float:
            return (x + y) * z

    a = A()

    # we can add hooks using decorators
    @a.f.add_pre_hook
    @monitor_calls(add_one_mock)
    def add_one(x: float, y: float, *, z: int) -> float:
        return x + 1

    @monitor_calls(deduct_one_mock)
    def deduct_one(x: float, y: float, *, z: int) -> float:
        return x - 1

    # or we can add hooks using function calls
    a.f.add_post_hook(deduct_one)

    # we cannot attach async function to sync one
    with pytest.raises(TypeError) as e:

        @a.f.add_pre_hook
        async def async_add_one(x: float, y: float, *, z: int) -> float:
            return x + 1

    assert str(e.value) == "Cannot attach async hook to sync function."

    assert a.f(1.1, 2.2, z=3) == (1.1 + 1 + 2.2) * 3 - 1

    add_one_mock.assert_called_once_with(1.1, 2.2, z=3)
    f_mock.assert_called_once_with(a, 2.1, 2.2, z=3)
    deduct_one_mock.assert_called_once_with((1.1 + 1 + 2.2) * 3, 2.2, z=3)


@pytest.mark.parametrize("cond", [None, Condition.true()])
@pytest.mark.asyncio()
async def test_hookable_method_async(cond: Condition) -> None:
    f_mock = AsyncMock()
    add_one_mock = MagicMock()
    deduct_one_mock = AsyncMock()

    class A:
        @hookable_method(cond=cond)
        @monitor_calls(f_mock)
        async def f(self, x: float, y: float, *, z: int) -> float:
            return (x + y) * z

    a = A()

    # cannot attach MagicMock to async function
    with pytest.raises(TypeError) as e:

        @a.f.add_pre_hook
        @monitor_calls(MagicMock())
        async def async_f(x: float, y: float, *, z: int) -> None:
            pass

    assert "Cannot attach sync mock to async function" in str(e.value)

    # we can add hooks using decorators
    @a.f.add_pre_hook
    @monitor_calls(add_one_mock)
    def add_one(x: float, y: float, *, z: int) -> float:
        return x + 1

    @monitor_calls(deduct_one_mock)
    async def deduct_one(x: float, y: float, *, z: int) -> float:
        return x - 1

    # or we can add hooks using function calls
    a.f.add_post_hook(deduct_one)

    assert await a.f(1.1, 2.2, z=3) == (1.1 + 1 + 2.2) * 3 - 1

    add_one_mock.assert_called_once_with(1.1, 2.2, z=3)
    f_mock.assert_awaited_once_with(a, 2.1, 2.2, z=3)
    deduct_one_mock.assert_awaited_once_with((1.1 + 1 + 2.2) * 3, 2.2, z=3)


@pytest.mark.parametrize("cond", [None, Condition.true()])
def test_hookable_function_sync(cond: Condition) -> None:
    g_mock = MagicMock()
    add_one_mock = MagicMock()
    deduct_one_mock = MagicMock()

    @hookable_function()
    @monitor_calls(g_mock)
    def g(x: float, y: float, *, z: int) -> float:
        return (x + y) * z

    # we can add hooks using decorators
    @g.add_pre_hook
    @monitor_calls(add_one_mock)
    def add_one(x: float, y: float, *, z: int) -> float:
        return x + 1

    @monitor_calls(deduct_one_mock)
    def deduct_one(x: float, y: float, *, z: int) -> float:
        return x - 1

    # or we can add hooks using function calls
    g.add_post_hook(deduct_one)

    assert g(1.1, 2.2, z=3) == (1.1 + 1 + 2.2) * 3 - 1
    add_one_mock.assert_called_once_with(1.1, 2.2, z=3)
    g_mock.assert_called_once_with(2.1, 2.2, z=3)
    deduct_one_mock.assert_called_once_with((1.1 + 1 + 2.2) * 3, 2.2, z=3)


@pytest.mark.parametrize("cond", [None, Condition.true])
@pytest.mark.asyncio()
async def test_hookable_function_async(cond: Condition) -> None:
    g_mock = AsyncMock()
    add_one_mock = AsyncMock()
    deduct_one_mock = MagicMock()

    @hookable_function()
    @monitor_calls(g_mock)
    async def g(x: float, y: float, *, z: int) -> float:
        return (x + y) * z

    # we can add hooks using decorators
    @g.add_pre_hook
    @monitor_calls(add_one_mock)
    async def add_one(x: [float], y: float, *, z: int) -> float:
        return x + 1

    @monitor_calls(deduct_one_mock)
    def deduct_one(x: float, y: float, *, z: int) -> float:
        return x - 1

    # or we can add hooks using function calls
    g.add_post_hook(deduct_one)

    assert await g(1.1, 2.2, z=3) == (1.1 + 1 + 2.2) * 3 - 1
    add_one_mock.assert_awaited_once_with(1.1, 2.2, z=3)
    g_mock.assert_awaited_once_with(2.1, 2.2, z=3)
    deduct_one_mock.assert_called_once_with((1.1 + 1 + 2.2) * 3, 2.2, z=3)


def test_hookable_function_with_condition():
    from typing import Union
    from autogen.middleware.hooks import hookable_method
    from autogen.middleware.conditions import Condition as C

    class A:
        # hooks are only executed if the condition is met (the first argument being an instance of float)
        @hookable_method(C.isinstance(float))
        def f(self, x: Union[int, float], y: float, *, z: int):
            return (x + y) * z

    a = A()

    # we can add hooks using decorators
    @a.f.add_pre_hook
    def add_one(x: Union[int, float], y: float, *, z: int):
        return x + 1

    def deduct_one(x: Union[int, float], y: float, *, z: int):
        return x - 1

    # or we can add hooks using function calls
    a.f.add_post_hook(deduct_one)

    # all hooks are executed
    assert a.f(1.1, 2.2, z=3) == (1.1 + 1 + 2.2) * 3 - 1
    # the pre-hook is not executed because the the first argument is not an instance of float
    assert a.f(1, 2.2, z=3) == (1 + 2.2) * 3 - 1
