"""This example demonstrates a human user interacting with a coder agent
which uses a model to generate code snippets. The user and the coder agent
takes turn to write input or generate code snippets, orchestrated by an
round-robin orchestrator agent.
The code snippets are not executed in this example."""

import asyncio
import logging

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.application.logging import EVENT_LOGGER_NAME
from autogen_core.base import AgentId, AgentProxy

# from typing import Any, Dict, List, Tuple, Union
from autogen_magentic_one.agents.coder import Coder
from autogen_magentic_one.agents.orchestrator import RoundRobinOrchestrator
from autogen_magentic_one.agents.user_proxy import UserProxy
from autogen_magentic_one.messages import RequestReplyMessage
from autogen_magentic_one.utils import LogHandler, create_completion_client_from_env


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Get an appropriate client
    client = create_completion_client_from_env()

    # Register agents.
    await Coder.register(runtime, "Coder", lambda: Coder(model_client=client))
    coder = AgentProxy(AgentId("Coder", "default"), runtime)

    await UserProxy.register(runtime, "UserProxy", lambda: UserProxy())
    user_proxy = AgentProxy(AgentId("UserProxy", "default"), runtime)

    await RoundRobinOrchestrator.register(runtime, "orchestrator", lambda: RoundRobinOrchestrator([coder, user_proxy]))

    runtime.start()
    await runtime.send_message(RequestReplyMessage(), user_proxy.id)
    await runtime.stop_when_idle()


if __name__ == "__main__":
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    log_handler = LogHandler()
    logger.handlers = [log_handler]
    asyncio.run(main())
