import asyncio
import logging
import platform

from autogen_core.application import WorkerAgentRuntimeHost
from autogen_core.application.logging import TRACE_LOGGER_NAME


async def run_host():
    host = WorkerAgentRuntimeHost(address="localhost:50051")
    host.start()  # Start a host service in the background.
    if platform.system() == "Windows":
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await host.stop()
    else:
        await host.stop_when_signal()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(f"{TRACE_LOGGER_NAME}.host")
    asyncio.run(run_host())
