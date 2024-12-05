import asyncio
import logging
import signal
from typing import Optional, Sequence

from ._constants import GRPC_IMPORT_ERROR_STR
from ._type_helpers import ChannelArgumentType
from ._worker_runtime_host_servicer import GrpcWorkerAgentRuntimeHostServicer

try:
    import grpc
except ImportError as e:
    raise ImportError(GRPC_IMPORT_ERROR_STR) from e
from .protos import agent_worker_pb2_grpc

logger = logging.getLogger("autogen_core")


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
        """Stop the server when a signal is received."""
        if self._serve_task is None:
            raise RuntimeError("Host runtime is not started.")
        # Set up signal handling for graceful shutdown.
        loop = asyncio.get_running_loop()
        shutdown_event = asyncio.Event()

        def signal_handler() -> None:
            logger.info("Received exit signal, shutting down gracefully...")
            shutdown_event.set()

        for sig in signals:
            loop.add_signal_handler(sig, signal_handler)

        # Wait for the signal to trigger the shutdown event.
        await shutdown_event.wait()

        # Shutdown the server.
        await self.stop(grace=grace)
