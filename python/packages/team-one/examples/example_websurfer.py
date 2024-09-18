import asyncio
import logging
import os

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.application.logging import EVENT_LOGGER_NAME
from autogen_core.base import AgentId, AgentProxy
from autogen_core.components import DefaultSubscription
from team_one.agents.multimodal_web_surfer import MultimodalWebSurfer
from team_one.agents.orchestrator import RoundRobinOrchestrator
from team_one.agents.user_proxy import UserProxy
from team_one.messages import RequestReplyMessage
from team_one.utils import LogHandler, create_completion_client_from_env

# NOTE: Don't forget to 'playwright install --with-deps chromium'


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Create an appropriate client
    client = create_completion_client_from_env()

    # Register agents.
    await runtime.register("WebSurfer", lambda: MultimodalWebSurfer(), lambda: [DefaultSubscription()])
    web_surfer = AgentProxy(AgentId("WebSurfer", "default"), runtime)

    await runtime.register("UserProxy", lambda: UserProxy(), lambda: [DefaultSubscription()])
    user_proxy = AgentProxy(AgentId("UserProxy", "default"), runtime)

    await runtime.register(
        "orchestrator", lambda: RoundRobinOrchestrator([web_surfer, user_proxy]), lambda: [DefaultSubscription()]
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
