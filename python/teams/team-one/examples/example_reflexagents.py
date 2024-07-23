import asyncio
import logging

from agnext.application import SingleThreadedAgentRuntime
from agnext.application.logging import EVENT_LOGGER_NAME
from agnext.components.models import UserMessage
from team_one.agents.orchestrator import RoundRobinOrchestrator
from team_one.agents.reflex_agents import ReflexAgent
from team_one.messages import BroadcastMessage
from team_one.utils import LogHandler


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()

    fake1 = await runtime.register_and_get_proxy("fake_agent_1", lambda: ReflexAgent("First reflect agent"))
    fake2 = await runtime.register_and_get_proxy("fake_agent_2", lambda: ReflexAgent("Second reflect agent"))
    fake3 = await runtime.register_and_get_proxy("fake_agent_3", lambda: ReflexAgent("Third reflect agent"))
    await runtime.register_and_get("orchestrator", lambda: RoundRobinOrchestrator([fake1, fake2, fake3]))

    task_message = UserMessage(content="Test Message", source="User")
    run_context = runtime.start()
    await runtime.publish_message(BroadcastMessage(task_message), namespace="default")

    await run_context.stop_when_idle()


if __name__ == "__main__":
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    log_handler = LogHandler()
    logger.handlers = [log_handler]
    asyncio.run(main())
