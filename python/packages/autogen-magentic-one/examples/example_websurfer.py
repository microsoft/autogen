"""This example demonstrates a human user interacting with a web surfer agent
to navigate the web through an embedded incognito browser.
The human user and the web surfer agent takes turn to write input or perform actions,
orchestrated by an round-robin orchestrator agent."""

import asyncio
import logging
import os

from autogen_core import EVENT_LOGGER_NAME, AgentId, AgentProxy, SingleThreadedAgentRuntime
from autogen_magentic_one.agents.multimodal_web_surfer import MultimodalWebSurfer
from autogen_magentic_one.agents.orchestrator import RoundRobinOrchestrator
from autogen_magentic_one.agents.user_proxy import UserProxy
from autogen_magentic_one.messages import RequestReplyMessage
from autogen_magentic_one.utils import LogHandler, create_completion_client_from_env

# NOTE: Don't forget to 'playwright install --with-deps chromium'


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Create an appropriate client
    client = create_completion_client_from_env(model="gpt-4o")

    # Register agents.
    await MultimodalWebSurfer.register(runtime, "WebSurfer", MultimodalWebSurfer)
    web_surfer = AgentProxy(AgentId("WebSurfer", "default"), runtime)

    await UserProxy.register(runtime, "UserProxy", UserProxy)
    user_proxy = AgentProxy(AgentId("UserProxy", "default"), runtime)

    await RoundRobinOrchestrator.register(
        runtime, "orchestrator", lambda: RoundRobinOrchestrator([web_surfer, user_proxy])
    )

    runtime.start()

    actual_surfer = await runtime.try_get_underlying_agent_instance(web_surfer.id, type=MultimodalWebSurfer)
    await actual_surfer.init(
        model_client=client,
        downloads_folder=os.getcwd(),
        start_page="https://www.bing.com",
        browser_channel="chromium",
    )

    await runtime.send_message(RequestReplyMessage(), user_proxy.id)
    await runtime.stop_when_idle()


if __name__ == "__main__":
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    log_handler = LogHandler()
    logger.handlers = [log_handler]
    asyncio.run(main())
