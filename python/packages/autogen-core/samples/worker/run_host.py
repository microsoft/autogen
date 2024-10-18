import asyncio

from autogen_core.application import WorkerAgentRuntimeHost


async def main() -> None:
    service = WorkerAgentRuntimeHost(address="localhost:50051")
    service.start()
    await service.stop_when_signal()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("autogen_core").setLevel(logging.DEBUG)
    asyncio.run(main())
