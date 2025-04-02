import asyncio
import typing as t
from functools import partial
from typing import Protocol

import asyncio_atexit
import pytest


class AtExitImpl(Protocol):
    def register(self, func: t.Callable[..., t.Any], /, *args: t.Any, **kwargs: t.Any) -> t.Callable[..., t.Any]: ...
    def unregister(self, func: t.Callable[..., t.Any], /) -> None: ...


class AtExitSimulator(AtExitImpl):
    def __init__(self) -> None:
        self._funcs: t.List[t.Callable[..., t.Any]] = []

    def complete(self) -> None:
        for func in self._funcs:
            func()

        self._funcs.clear()

    def register(self, func: t.Callable[..., t.Any], /, *args: t.Any, **kwargs: t.Any) -> t.Callable[..., t.Any]:
        self._funcs.append(func)
        return func

    def unregister(self, func: t.Callable[..., t.Any], /) -> None:
        self._funcs.remove(func)


class AsyncioAtExitWrapper(AtExitImpl):
    """This only exists to make mypy happy"""

    def register(self, func: t.Callable[..., t.Any], /, *args: t.Any, **kwargs: t.Any) -> t.Callable[..., t.Any]:
        loop = None
        if "loop" in kwargs:
            loop = kwargs["loop"]
            kwargs.pop("loop")

        wrapper = partial(func, *args, **kwargs)

        asyncio_atexit.register(wrapper, loop=loop)  # type: ignore

        return func

    def unregister(self, func: t.Callable[..., t.Any], /, **kwargs: t.Any) -> None:
        loop = None
        if "loop" in kwargs:
            loop = kwargs["loop"]
            kwargs.pop("loop")

        asyncio_atexit.unregister(func, loop=loop)  # type: ignore


# This is a minimal implementation of a component that requires cleanup on exit.
class CleanupComponent:
    def __init__(self, atexit_impl: AtExitImpl, use_async_cleanup: bool) -> None:
        self.atexit_impl = atexit_impl
        self.cleanup_has_run = False
        self.stop_has_run = False

        self.cleanup = self._acleanup if use_async_cleanup else self._cleanup
        self.atexit_impl.register(self.cleanup)

    async def stop(self) -> None:
        self.stop_has_run = True

    async def _acleanup(self) -> None:
        self.cleanup_has_run = True
        await self.stop()

    def _cleanup(self) -> None:
        self.cleanup_has_run = True
        loop = asyncio.get_running_loop()
        loop.run_until_complete(self.stop())


async def create_component(atexit_impl: AtExitImpl, /, use_async_cleanup: bool) -> CleanupComponent:
    await asyncio.sleep(0.001)
    return CleanupComponent(atexit_impl, use_async_cleanup)


def run_test_impl(debug_printer: t.Callable[[str], t.Any] | None = None) -> None:
    def validate(component: CleanupComponent, expect_exception: bool, expect_stop: bool) -> None:
        if debug_printer is not None:
            debug_printer(f"Cleanup ran: {component.cleanup_has_run} (expected True)")
            debug_printer(f"Stop ran: {component.stop_has_run} (expected {expect_stop})")

        assert component.cleanup_has_run, "Cleanup should always run to be a faithful simulation."
        assert component.stop_has_run == expect_stop

    # AtExitSimulator behaves like atexit.register, while causes cleanup relying on it to fail.
    atexit_simulator = AtExitSimulator()
    loop = asyncio.new_event_loop()
    component = loop.run_until_complete(create_component(atexit_simulator, use_async_cleanup=False))
    loop.close()

    with pytest.raises(RuntimeError):
        atexit_simulator.complete()

    validate(component, expect_exception=True, expect_stop=False)

    loop = asyncio.new_event_loop()
    component = loop.run_until_complete(create_component(AsyncioAtExitWrapper(), use_async_cleanup=True))
    loop.close()
    validate(component, expect_exception=False, expect_stop=True)


def test_asyncio_atexit_assumptions() -> None:
    run_test_impl()


if __name__ == "__main__":
    debug_printer = print
    run_test_impl(debug_printer=debug_printer)
