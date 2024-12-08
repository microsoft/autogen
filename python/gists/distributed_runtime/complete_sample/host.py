import argparse
import asyncio

from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost


async def main(host_address: str):
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()
    print(f"Host started at {host_address}")
    await host.stop_when_signal()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the UI Agent with specified parameters.")
    parser.add_argument(
        "--host-address", type=str, help="The address of the host to connect to.", default="localhost:5000"
    )
    args = parser.parse_args()

    grpc_host: str = args.host_address

    asyncio.run(main(host_address=args.host_address))
