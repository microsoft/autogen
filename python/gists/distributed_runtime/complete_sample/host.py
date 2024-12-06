import asyncio

from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost


async def main(host_address: str):
    host = GrpcWorkerAgentRuntimeHost(address=host_address)
    host.start()
    print(f"Host started at {host_address}")
    await host.stop_when_signal()


if __name__ == "__main__":
    asyncio.run(main(host_address="localhost:5000"))
