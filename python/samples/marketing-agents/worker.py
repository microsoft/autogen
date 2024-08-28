import asyncio
import logging

from app import build_app
from autogen_core.application import WorkerAgentRuntime
from autogen_core.base import MESSAGE_TYPE_REGISTRY
from dotenv import load_dotenv
from messages import ArticleCreated, AuditorAlert, AuditText, GraphicDesignCreated

agnext_logger = logging.getLogger("autogen_core")


async def main() -> None:
    load_dotenv()
    runtime = WorkerAgentRuntime()
    MESSAGE_TYPE_REGISTRY.add_type(ArticleCreated)
    MESSAGE_TYPE_REGISTRY.add_type(GraphicDesignCreated)
    MESSAGE_TYPE_REGISTRY.add_type(AuditText)
    MESSAGE_TYPE_REGISTRY.add_type(AuditorAlert)
    agnext_logger.info("1")
    await runtime.start("localhost:5145")

    agnext_logger.info("2")

    await build_app(runtime)
    agnext_logger.info("3")

    # just to keep the runtime running
    try:
        await asyncio.sleep(1000000)
    except KeyboardInterrupt:
        pass
    await runtime.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    agnext_logger.setLevel(logging.DEBUG)
    agnext_logger.log(logging.DEBUG, "Starting worker")
    asyncio.run(main())
