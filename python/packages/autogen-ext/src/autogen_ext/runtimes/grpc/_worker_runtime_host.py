import asyncio
import logging
import os
import signal
from typing import Any, Optional, Sequence

from ._constants import GRPC_IMPORT_ERROR_STR
from ._type_helpers import ChannelArgumentType
from ._worker_runtime_host_servicer import GrpcWorkerAgentRuntimeHostServicer

try:
    import grpc
except ImportError as e:
    raise ImportError(GRPC_IMPORT_ERROR_STR) from e
from .protos import agent_worker_pb2_grpc

logger = logging.getLogger("autogen_core")


def is_running_in_container() -> bool:
    """
    Detect if the process is running inside a container environment.

    Returns:
        bool: True if running in a container, False otherwise.

    .. versionadded:: v0.4.1
       Added container environment detection for improved signal handling.
    """
    # Check for common container indicators
    container_indicators = [
        # Docker container
        os.path.exists("/.dockerenv"),
        # Kubernetes pod
        os.path.exists("/var/run/secrets/kubernetes.io"),
        # Azure Container Apps
        os.environ.get("CONTAINER_APP_NAME") is not None,
        # Generic container environment variables
        os.environ.get("CONTAINER") == "true",
        os.environ.get("DOCKER_CONTAINER") == "true",
    ]

    return any(container_indicators)


def is_pid_1() -> bool:
    """
    Check if the current process is running as PID 1.

    Returns:
        bool: True if running as PID 1, False otherwise.

    .. versionadded:: v0.4.1
       Added PID 1 detection for improved signal handling in containers.
    """
    return os.getpid() == 1


async def _robust_signal_handler(
    shutdown_event: asyncio.Event, signals: Sequence[signal.Signals] = (signal.SIGTERM, signal.SIGINT)
) -> None:
    """
    Robust signal handling that works in container environments.

    This function implements multiple signal handling strategies:
    1. asyncio.loop.add_signal_handler (standard approach)
    2. signal.signal with threading (fallback for containers)
    3. Periodic signal checking (fallback for PID 1 scenarios)

    Args:
        shutdown_event: Event to set when a signal is received
        signals: Sequence of signals to handle

    .. versionadded:: v0.4.1
       Added robust signal handling for container environments.
    """
    import threading
    import time

    def signal_handler_callback(signum: int, frame: object | None) -> None:
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        shutdown_event.set()

    # Strategy 1: Try asyncio signal handling (works in most cases)
    try:
        loop = asyncio.get_running_loop()
        for sig in signals:
            loop.add_signal_handler(sig, lambda: shutdown_event.set())
        logger.debug("Using asyncio signal handling")
        return
    except (NotImplementedError, RuntimeError, OSError) as e:
        logger.debug(f"asyncio signal handling failed: {e}, trying fallback methods")

    # Strategy 2: Use signal.signal with threading (works in containers)
    try:
        for sig in signals:
            signal.signal(sig, signal_handler_callback)
        logger.debug("Using signal.signal handling")
        return
    except (OSError, ValueError) as e:
        logger.debug(f"signal.signal handling failed: {e}, using periodic checking")

    # Strategy 3: Periodic signal checking (last resort for PID 1)
    # This is needed when running as PID 1 in some container environments
    def periodic_signal_check() -> None:
        original_handlers: dict[signal.Signals, Any] = {}
        try:
            # Set up signal handlers
            for sig in signals:
                try:
                    original_handlers[sig] = signal.signal(sig, signal_handler_callback)
                except (OSError, ValueError):
                    pass

            # Periodically check if we're still running
            while not shutdown_event.is_set():
                time.sleep(0.1)
        finally:
            # Restore original handlers
            for sig, handler in original_handlers.items():
                try:
                    signal.signal(sig, handler)
                except (OSError, ValueError):
                    pass

    # Run periodic checking in a separate thread
    signal_thread = threading.Thread(target=periodic_signal_check, daemon=True)
    signal_thread.start()
    logger.debug("Using periodic signal checking")


class GrpcWorkerAgentRuntimeHost:
    def __init__(self, address: str, extra_grpc_config: Optional[ChannelArgumentType] = None) -> None:
        self._server = grpc.aio.server(options=extra_grpc_config)
        self._servicer = GrpcWorkerAgentRuntimeHostServicer()
        agent_worker_pb2_grpc.add_AgentRpcServicer_to_server(self._servicer, self._server)
        self._server.add_insecure_port(address)
        self._address = address
        self._serve_task: asyncio.Task[None] | None = None

    async def _serve(self) -> None:
        await self._server.start()
        logger.info(f"Server started at {self._address}.")
        await self._server.wait_for_termination()

    def start(self) -> None:
        """Start the server in a background task."""
        if self._serve_task is not None:
            raise RuntimeError("Host runtime is already started.")
        self._serve_task = asyncio.create_task(self._serve())

    async def stop(self, grace: int = 5) -> None:
        """Stop the server."""
        if self._serve_task is None:
            raise RuntimeError("Host runtime is not started.")
        await self._server.stop(grace=grace)
        self._serve_task.cancel()
        try:
            await self._serve_task
        except asyncio.CancelledError:
            pass
        logger.info("Server stopped.")
        self._serve_task = None

    async def stop_when_signal(
        self, grace: int = 5, signals: Sequence[signal.Signals] = (signal.SIGTERM, signal.SIGINT)
    ) -> None:
        """
        Stop the server when a signal is received.

        This method uses robust signal handling that works in container environments,
        including Azure Container Apps, Docker, and Kubernetes.

        Args:
            grace: Grace period in seconds for server shutdown
            signals: Sequence of signals to handle (default: SIGTERM, SIGINT)

        Raises:
            RuntimeError: If the host runtime is not started

        .. versionchanged:: v0.4.1
           Improved signal handling for container environments including Azure Container Apps.
        """
        if self._serve_task is None:
            raise RuntimeError("Host runtime is not started.")

        # Detect container environment for logging
        in_container = is_running_in_container()
        is_pid_1_result = is_pid_1()

        if in_container:
            logger.info(f"Detected container environment (PID 1: {is_pid_1_result}), using robust signal handling")

        # Set up robust signal handling for graceful shutdown
        shutdown_event = asyncio.Event()

        # Start the robust signal handler
        await _robust_signal_handler(shutdown_event, signals)

        # Wait for the signal to trigger the shutdown event.
        await shutdown_event.wait()

        # Shutdown the server.
        await self.stop(grace=grace)
