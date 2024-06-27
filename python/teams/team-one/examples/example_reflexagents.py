import asyncio

from agnext.application import SingleThreadedAgentRuntime
from team_one.agents.orchestrator import RoundRobinOrchestrator
from team_one.agents.reflex_agents import ReflexAgent
from team_one.messages import BroadcastMessage


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()

    fake1 = runtime.register_and_get_proxy("fake_agent_1", lambda: ReflexAgent("First reflect agent"))
    fake2 = runtime.register_and_get_proxy("fake_agent_2", lambda: ReflexAgent("Second reflect agent"))
    fake3 = runtime.register_and_get_proxy("fake_agent_3", lambda: ReflexAgent("Third reflect agent"))
    runtime.register_and_get("orchestrator", lambda: RoundRobinOrchestrator([fake1, fake2, fake3]))

    await runtime.publish_message(BroadcastMessage("Test message"), namespace="default")

    await runtime.process_until_idle()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)

    asyncio.run(main())
