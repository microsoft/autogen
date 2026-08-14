import asyncio

from _types import HostConfig
from _utils import load_config
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost
from rich.console import Console
from rich.markdown import Markdown


async def main(host_config: HostConfig):
    host = GrpcWorkerAgentRuntimeHost(address=host_config.address)
    host.start()

    console = Console()
    console.print(
        Markdown(f"**`Distributed Host`** is now running and listening for connection at **`{host_config.address}`**")
    )
    await host.stop_when_signal()


if __name__ == "__main__":
    asyncio.run(main(load_config().host))
