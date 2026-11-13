import asyncio
import logging
import signal
from collections.abc import Sequence
from types import FrameType
from typing import Any

logger = logging.getLogger("autogen_core")


async def wait_for_signal(signals: Sequence[signal.Signals]) -> None:
    """Wait for one of *signals* on event loops with or without signal support."""
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()
    unique_signals = tuple(dict.fromkeys(signals))
    loop_signals: list[signal.Signals] = []
    previous_handlers: dict[signal.Signals, Any] = {}

    def signal_handler() -> None:
        logger.info("Received exit signal, shutting down gracefully...")
        shutdown_event.set()

    def fallback_signal_handler(_signum: int, _frame: FrameType | None) -> None:
        loop.call_soon_threadsafe(signal_handler)

    try:
        try:
            for sig in unique_signals:
                loop.add_signal_handler(sig, signal_handler)
                loop_signals.append(sig)
        except NotImplementedError:
            # Windows' default event loop does not implement add_signal_handler.
            for sig in loop_signals:
                loop.remove_signal_handler(sig)
            loop_signals.clear()

            for sig in unique_signals:
                previous_handlers[sig] = signal.signal(sig, fallback_signal_handler)

        await shutdown_event.wait()
    finally:
        for sig in loop_signals:
            loop.remove_signal_handler(sig)
        for sig, previous_handler in previous_handlers.items():
            signal.signal(sig, previous_handler)
