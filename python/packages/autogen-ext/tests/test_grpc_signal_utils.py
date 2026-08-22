import asyncio
import signal
from collections.abc import Callable
from types import FrameType
from typing import Any

import pytest
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime
from autogen_ext.runtimes.grpc._signal_utils import wait_for_signal


@pytest.mark.asyncio
async def test_wait_for_signal_uses_and_removes_loop_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = asyncio.get_running_loop()
    installed_handlers: dict[signal.Signals, Callable[[], None]] = {}
    removed_signals: list[signal.Signals] = []

    def add_signal_handler(sig: signal.Signals, callback: Callable[[], None], *args: Any) -> None:
        installed_handlers[sig] = callback

    def remove_signal_handler(sig: signal.Signals) -> bool:
        removed_signals.append(sig)
        return True

    monkeypatch.setattr(loop, "add_signal_handler", add_signal_handler)
    monkeypatch.setattr(loop, "remove_signal_handler", remove_signal_handler)

    wait_task = asyncio.create_task(wait_for_signal((signal.SIGINT,)))
    await asyncio.sleep(0)
    installed_handlers[signal.SIGINT]()
    await wait_task

    assert removed_signals == [signal.SIGINT]


@pytest.mark.asyncio
async def test_worker_runtime_falls_back_and_restores_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = asyncio.get_running_loop()
    installed_handlers: dict[signal.Signals, signal.Handlers | Callable[[int, FrameType | None], Any]] = {}
    previous_handler = signal.SIG_DFL

    def unsupported_signal_handler(sig: signal.Signals, callback: Callable[[], None], *args: Any) -> None:
        raise NotImplementedError

    def replace_signal_handler(
        sig: signal.Signals, handler: signal.Handlers | Callable[[int, FrameType | None], Any]
    ) -> signal.Handlers | Callable[[int, FrameType | None], Any]:
        old_handler = installed_handlers.get(sig, previous_handler)
        installed_handlers[sig] = handler
        return old_handler

    monkeypatch.setattr(loop, "add_signal_handler", unsupported_signal_handler)
    monkeypatch.setattr(signal, "signal", replace_signal_handler)

    runtime = GrpcWorkerAgentRuntime(host_address="unused")
    runtime._running = True  # type: ignore[reportPrivateUsage]
    wait_task = asyncio.create_task(runtime.stop_when_signal((signal.SIGINT, signal.SIGINT)))
    await asyncio.sleep(0)

    fallback_handler = installed_handlers[signal.SIGINT]
    assert callable(fallback_handler)
    fallback_handler(signal.SIGINT, None)
    await wait_task

    assert not runtime._running  # type: ignore[reportPrivateUsage]
    assert installed_handlers[signal.SIGINT] is previous_handler
