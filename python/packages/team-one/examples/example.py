"""This example demonstrates a human user interacting with a coder agent and a executor agent
to generate and execute code snippets. An ledger orchestrator agent orchestrates the interaction
between the user, coder, and executor agents.
At each step, the orchestrator agent decides which user or agent to perform the next action.
The code snippets are executed inside a docker container."""

import asyncio
import logging

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.application.logging import EVENT_LOGGER_NAME
from autogen_core.base import AgentId, AgentProxy
from autogen_core.components.code_executor._impl.docker_command_line_code_executor import DockerCommandLineCodeExecutor
from team_one.agents.coder import Coder, Executor
from team_one.agents.orchestrator import LedgerOrchestrator
from team_one.agents.user_proxy import UserProxy
from team_one.messages import RequestReplyMessage
from team_one.utils import LogHandler, create_completion_client_from_env


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    async with DockerCommandLineCodeExecutor() as code_executor:
        # Register agents.
        await Coder.register(runtime, "Coder", lambda: Coder(model_client=create_completion_client_from_env()))
        coder = AgentProxy(AgentId("Coder", "default"), runtime)

        await Executor.register(
            runtime,
            "Executor",
            lambda: Executor("A agent for executing code", executor=code_executor),
        )
        executor = AgentProxy(AgentId("Executor", "default"), runtime)

        await UserProxy.register(
            runtime,
            "UserProxy",
            lambda: UserProxy(description="The current user interacting with you."),
        )
        user_proxy = AgentProxy(AgentId("UserProxy", "default"), runtime)

        # TODO: doesn't work for more than default key
        await LedgerOrchestrator.register(
            runtime,
            "orchestrator",
            lambda: LedgerOrchestrator(
                model_client=create_completion_client_from_env(), agents=[coder, executor, user_proxy]
            ),
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
