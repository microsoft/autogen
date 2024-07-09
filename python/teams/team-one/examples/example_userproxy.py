import asyncio
import logging

# from typing import Any, Dict, List, Tuple, Union
from agnext.application import SingleThreadedAgentRuntime
from agnext.application.logging import EVENT_LOGGER_NAME
from team_one.agents.coder import Coder
from team_one.agents.orchestrator import RoundRobinOrchestrator
from team_one.agents.user_proxy import UserProxy
from team_one.messages import RequestReplyMessage
from team_one.utils import LogHandler, create_completion_client_from_env


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Get an appropriate client
    client = create_completion_client_from_env()

    # Register agents.
    coder = runtime.register_and_get_proxy(
        "Coder",
        lambda: Coder(model_client=client),
    )
    user_proxy = runtime.register_and_get_proxy(
        "UserProxy",
        lambda: UserProxy(),
    )

    runtime.register("orchestrator", lambda: RoundRobinOrchestrator([coder, user_proxy]))

    run_context = runtime.start()
    await runtime.send_message(RequestReplyMessage(), user_proxy.id)
    await run_context.stop_when_idle()


if __name__ == "__main__":
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    log_handler = LogHandler()
    logger.handlers = [log_handler]
    asyncio.run(main())
