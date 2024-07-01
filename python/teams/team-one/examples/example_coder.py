import asyncio

from agnext.application import SingleThreadedAgentRuntime
from agnext.components.models import OpenAIChatCompletionClient, UserMessage
from team_one.agents.coder import Coder, Executor
from team_one.agents.orchestrator import RoundRobinOrchestrator
from team_one.messages import BroadcastMessage


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    client = OpenAIChatCompletionClient(model="gpt-4o")

    # Register agents.
    coder = runtime.register_and_get_proxy(
        "Coder",
        lambda: Coder(model_client=client),
    )
    executor = runtime.register_and_get_proxy("Executor", lambda: Executor("A agent for executing code"))

    runtime.register("orchestrator", lambda: RoundRobinOrchestrator([coder, executor]))

    task = input("Enter a task: ")

    run_context = runtime.start()

    await runtime.publish_message(
        BroadcastMessage(content=UserMessage(content=task, source="human")), namespace="default"
    )

    # Run the runtime until the task is completed.
    await run_context.stop_when_idle()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
