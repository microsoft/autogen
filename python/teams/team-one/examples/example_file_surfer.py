import asyncio

from agnext.application import SingleThreadedAgentRuntime
from agnext.components.models import (
    OpenAIChatCompletionClient,
)
from team_one.agents.file_surfer import FileSurfer
from team_one.messages import LLMResponseMessage, TaskMessage


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Register agents.
    file_surfer = runtime.register_and_get(
        "file_surfer",
        lambda: FileSurfer(model_client=OpenAIChatCompletionClient(model="gpt-4o")),
    )

    task = TaskMessage(input(f"Enter a task for {file_surfer.name}: "))

    # Send a task to the tool user.
    result = await runtime.send_message(task, file_surfer)

    # Run the runtime until the task is completed.
    while not result.done():
        await runtime.process_next()

    # Print the result.
    final_response = result.result()
    assert isinstance(final_response, LLMResponseMessage)
    print("--------------------")
    print(final_response.content)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
