import asyncio
import logging

from agnext.application import SingleThreadedAgentRuntime
from agnext.application.logging import EVENT_LOGGER_NAME
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
    web_surfer = runtime.register_and_get_proxy(
        "WebSurfer",
        lambda: MultimodalWebSurfer(),
    )

    user_proxy = runtime.register_and_get_proxy(
        "UserProxy",
        lambda: UserProxy(),
    )

    runtime.register("orchestrator", lambda: RoundRobinOrchestrator([web_surfer, user_proxy]))

    run_context = runtime.start()

    actual_surfer = runtime._get_agent(web_surfer.id)  # type: ignore
    assert isinstance(actual_surfer, MultimodalWebSurfer)
    await actual_surfer.init(model_client=client, browser_channel="chromium")

    await runtime.send_message(RequestReplyMessage(), user_proxy.id)
    await run_context.stop_when_idle()


if __name__ == "__main__":
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    log_handler = LogHandler()
    logger.handlers = [log_handler]
    asyncio.run(main())
