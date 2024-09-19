"""This example demonstrates a human user interacting with a coder agent and a executor agent
to generate and execute code snippets. The user and the agents take turn sequentially
to write input, generate code snippets and execute them, orchestrated by an
round-robin orchestrator agent. The code snippets are executed inside a docker container.
"""

import asyncio
import logging
from typing import Any

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.application.logging import EVENT_LOGGER_NAME
from autogen_core.base import AgentId, AgentProxy
from autogen_core.base.intervention import DefaultInterventionHandler, DropMessage
from autogen_core.components.code_executor import DockerCommandLineCodeExecutor
from team_one.agents.coder import Coder, Executor
from team_one.agents.orchestrator import RoundRobinOrchestrator
from team_one.agents.user_proxy import UserProxy
from team_one.messages import RequestReplyMessage
from team_one.utils import LogHandler, create_completion_client_from_env


class ConfirmCode(DefaultInterventionHandler):
    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any | type[DropMessage]:
        if sender is not None and sender.type == "Coder":
            print("Coder has generated the following code:")
            print(message)
            response = await asyncio.to_thread(input, "Do you want to proceed? (yes/no): ")
            if response.lower() != "yes":
                raise ValueError("User has rejected the message.")
        return message


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime(intervention_handlers=[ConfirmCode()])

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

        await RoundRobinOrchestrator.register(
            runtime,
            "orchestrator",
            lambda: RoundRobinOrchestrator([coder, executor, user_proxy]),
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
