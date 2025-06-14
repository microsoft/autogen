import asyncio
import logging

from _types import HostConfig
from _utils import load_config
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost
from rich.console import Console
from rich.markdown import Markdown


async def main(host_config: HostConfig):
    # Set up logging to see container detection messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    host = GrpcWorkerAgentRuntimeHost(address=host_config.address)
    host.start()

    console = Console()
    console.print(
        Markdown(f"**`Distributed Host`** is now running and listening for connection at **`{host_config.address}`**")
    )

    logger.info("Starting robust signal handling (works in Azure Container Apps, Docker, and Kubernetes)")

    try:
        await host.stop_when_signal()
    except Exception as e:
        logger.error(f"Error in signal handling: {e}")
        raise
    finally:
        logger.info("Host shutdown complete")


if __name__ == "__main__":
    asyncio.run(main(load_config().host))
