from agnext.worker.worker_runtime import WorkerAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import CancellationToken, AgentId
import logging
import asyncio
import os

from dataclasses import dataclass

@dataclass
class ExampleMessagePayload:
    content: str


class ExampleAgent(TypeRoutedAgent):
    def __init__(self) -> None:
        super().__init__("Example Agent")

    @message_handler
    async def on_example_payload(self, message: ExampleMessagePayload, cancellation_token: CancellationToken) -> None:
        upper_case = message.content.upper()
        await self.publish_message(ExampleMessagePayload(content=upper_case))


async def main() -> None:
    logger = logging.getLogger("main")
    runtime = WorkerAgentRuntime()
    await runtime.setup_channel(os.environ["AGENT_HOST"])

    runtime.register("ExampleAgent", lambda: ExampleAgent())
    while True:
        try:
            res = await runtime.send_message("testing!", recipient=AgentId(name="greeter", namespace="testing"), sender=AgentId(name="ExampleAgent", namespace="testing"))
            logger.info("Response: %s", res)
        except Exception as e:
            logger.warning("Error: %s", e)
        await asyncio.sleep(5)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())

