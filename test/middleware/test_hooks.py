import sys

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autogen.middleware.conditions import Condition
from autogen.middleware.hooks import await_if_needed, hookable_function, hookable_method

sys.path.append("../..")
from mocks import monitor_calls  # noqa: E402


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
    async def add_one(x: float, y: float, *, z: int) -> float:
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


def test_hookable_function_with_condition() -> None:
    from typing import Union

    from autogen.middleware.conditions import Condition as C
    from autogen.middleware.hooks import hookable_method

    class A:
        # hooks are only executed if the condition is met (the first argument being an instance of float)
        @hookable_method(C.isinstance(float))
        def f(self, x: Union[int, float], y: float, *, z: int) -> float:
            return (x + y) * z

    a = A()

    # we can add hooks using decorators
    @a.f.add_pre_hook
    def add_one(x: Union[int, float], y: float, *, z: int) -> float:
        return x + 1

    def deduct_one(x: Union[int, float], y: float, *, z: int) -> float:
        return x - 1

    # or we can add hooks using function calls
    a.f.add_post_hook(deduct_one)

    # all hooks are executed
    assert a.f(1.1, 2.2, z=3) == (1.1 + 1 + 2.2) * 3 - 1
    # the pre-hook is not executed because the the first argument is not an instance of float
    assert a.f(1, 2.2, z=3) == (1 + 2.2) * 3 - 1


# from contextlib import contextmanager


# @contextmanager
# def my_middleware(*args, **kwargs):
#     # do something before passing control to the next middleware
#     new_args = [arg + 1 for arg in args]
#     new_kwargs = {k: v + 1 for k, v in kwargs.items()}
#     try:
#         next_ret_args, next_ret_kwargs = yield new_args, new_kwargs
#     finally:
#         # do some cleanup after the next middleware has finished
#         pass
#     # do something after the next middleware has finished and return
#     ret_args = [arg + 1 for arg in next_ret_args]
#     ret_kwargs = {k: v + 1 for k, v in next_ret_kwargs.items()}

#     return ret_args, ret_kwargs


# class MyMiddleware():
#     def __init__(self, *args, **kwargs):
#         pass

#     def trigger(self, *args, **kwargs) -> bool:
#         return isinstance(args[0], int)

#     def call(self, *args, next_middleware=None, **kwargs) -> Any:
#         new_args = [arg + 1 for arg in args]
#         new_kwargs = {k: v + 1 for k, v in kwargs.items()}

#         try:
#             if next_middleware is not None:
#                 next_ret_args, next_ret_kwargs = next_middleware(*new_args, **new_kwargs)
#             else:
#                 next_ret_args, next_ret_kwargs = new_args, new_kwargs
#         finally:
#             pass

#         ret_args = [arg + 1 for arg in args]
#         ret_kwargs = {k: v + 1 for k, v in kwargs.items()}
#         return ret_args, ret_kwargs

# class ReplyMiddleware():
#     def __init__(self, *args, **kwargs):
#         pass

#     def trigger(self, sender: Agent, receiver: Agent, messages: List[Dict[str, Any]]) -> bool:
#         return isinstance(args[0], ConversibleAgent)

#     def call(self, *args, next=None, **kwargs) -> Any:
#         last_message = messages[-1]
#         # do some stuff with the last message
#         pass

#         messages = messages[:-1] + [last_message]

#         try:
#             if next_middleware is not None:
#                 next_ret_args, next_ret_kwargs = next_middleware(*new_args, **new_kwargs)
#             else:
#                 next_ret_args, next_ret_kwargs = new_args, new_kwargs
#         finally:
#             pass

#         ret_args = [arg + 1 for arg in args]
#         ret_kwargs = {k: v + 1 for k, v in kwargs.items()}
#         return ret_args, ret_kwargs
