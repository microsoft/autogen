import asyncio
import logging
import os

from agnext.worker.worker_runtime import WorkerAgentRuntime
from app import build_app


async def main() -> None:
    runtime = WorkerAgentRuntime()
    await runtime.setup_channel(os.environ["AGENT_HOST"])

    await build_app(runtime)

    # just to keep the runtime running
    try:
        await asyncio.sleep(1000000)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
