import asyncio

from agnext.application import SingleThreadedAgentRuntime
from agnext.components.models import UserMessage
from team_one.agents.file_surfer import FileSurfer
from team_one.messages import BroadcastMessage, RequestReplyMessage
from team_one.utils import create_completion_client_from_env


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Register agents.
    file_surfer = runtime.register_and_get(
        "file_surfer",
        lambda: FileSurfer(model_client=create_completion_client_from_env()),
    )
    task = input(f"Enter a task for {file_surfer.name}: ")
    msg = BroadcastMessage(content=UserMessage(content=task, source="human"))

    run_context = runtime.start()

    # Send a task to the tool user.
    await runtime.publish_message(msg, namespace="default")
    await runtime.publish_message(RequestReplyMessage(), namespace="default")

    # Run the runtime until the task is completed.
    await run_context.stop_when_idle()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
