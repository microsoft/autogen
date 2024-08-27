import asyncio
import logging

from agnext.application import SingleThreadedAgentRuntime
from agnext.application.logging import EVENT_LOGGER_NAME

# from typing import Any, Dict, List, Tuple, Union
from agnext.components import DefaultSubscription
from agnext.core import AgentId, AgentProxy
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
    await runtime.register("Coder", lambda: Coder(model_client=client), lambda: [DefaultSubscription()])
    coder = AgentProxy(AgentId("Coder", "default"), runtime)

    await runtime.register("UserProxy", lambda: UserProxy(), lambda: [DefaultSubscription()])
    user_proxy = AgentProxy(AgentId("UserProxy", "default"), runtime)

    await runtime.register(
        "orchestrator", lambda: RoundRobinOrchestrator([coder, user_proxy]), lambda: [DefaultSubscription()]
    )

    runtime.start()
    await runtime.send_message(RequestReplyMessage(), user_proxy.id)
    await runtime.stop_when_idle()


if __name__ == "__main__":
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    log_handler = LogHandler()
    logger.handlers = [log_handler]
    asyncio.run(main())
