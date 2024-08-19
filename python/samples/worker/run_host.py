import asyncio
import signal

import grpc
from agnext.application import HostRuntimeServicer
from agnext.application.protos import agent_worker_pb2_grpc


async def serve(server: grpc.aio.Server) -> None:  # type: ignore
    await server.start()
    print("Server started")
    await server.wait_for_termination()


async def main() -> None:
    server = grpc.aio.server()
    agent_worker_pb2_grpc.add_AgentRpcServicer_to_server(HostRuntimeServicer(), server)
    server.add_insecure_port("[::]:50051")

    # Set up signal handling for graceful shutdown
    loop = asyncio.get_running_loop()

    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        print("Received exit signal, shutting down gracefully...")
        shutdown_event.set()

    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)

    # Start server in background task
    serve_task = asyncio.create_task(serve(server))

    # Wait for the signal to trigger the shutdown event
    await shutdown_event.wait()

    # Graceful shutdown
    await server.stop(5)  # 5 second grace period
    await serve_task
    print("Server stopped")


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shutdown interrupted.")
