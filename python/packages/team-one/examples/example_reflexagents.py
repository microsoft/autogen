"""This example demonstrates three mock agents taking turn to reflect recieved message
by publishing it verbatim. The agents are orchestrated by a round-robin orchestrator agent."""

import asyncio
import logging

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.application.logging import EVENT_LOGGER_NAME
from autogen_core.base import AgentId, AgentProxy
from autogen_core.components import DefaultTopicId
from autogen_core.components.models import UserMessage
from team_one.agents.orchestrator import RoundRobinOrchestrator
from team_one.agents.reflex_agents import ReflexAgent
from team_one.messages import BroadcastMessage
from team_one.utils import LogHandler


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()

    await ReflexAgent.register(runtime, "fake_agent_1", lambda: ReflexAgent("First reflect agent"))
    fake1 = AgentProxy(AgentId("fake_agent_1", "default"), runtime)

    await ReflexAgent.register(runtime, "fake_agent_2", lambda: ReflexAgent("Second reflect agent"))
    fake2 = AgentProxy(AgentId("fake_agent_2", "default"), runtime)

    await ReflexAgent.register(runtime, "fake_agent_3", lambda: ReflexAgent("Third reflect agent"))
    fake3 = AgentProxy(AgentId("fake_agent_3", "default"), runtime)

    await RoundRobinOrchestrator.register(
        runtime, "orchestrator", lambda: RoundRobinOrchestrator([fake1, fake2, fake3])
    )

    task_message = UserMessage(content="Test Message", source="User")
    runtime.start()
    await runtime.publish_message(BroadcastMessage(content=task_message), topic_id=DefaultTopicId())

    await runtime.stop_when_idle()


if __name__ == "__main__":
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    log_handler = LogHandler()
    logger.handlers = [log_handler]
    asyncio.run(main())
