import asyncio
import os

from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost


async def main() -> None:
    service = GrpcWorkerAgentRuntimeHost(address="localhost:50051")
    service.start()

    try:
        # Wait for the service to stop
        if os.name == "nt":
            # On Windows, the signal is not available, so we wait for a new event
            await asyncio.Event().wait()
        else:
            await service.stop_when_signal()
    except KeyboardInterrupt:
        print("Stopping service...")
    finally:
        await service.stop()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("autogen_core").setLevel(logging.DEBUG)
    asyncio.run(main())
