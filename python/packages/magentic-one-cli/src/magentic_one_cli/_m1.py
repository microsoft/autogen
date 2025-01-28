import argparse
import asyncio
import warnings
from typing import Optional

from autogen_agentchat.ui import Console, UserInputManager
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_ext.ui import RichConsole

# Suppress warnings about the requests.Session() not being closed
warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)


async def cancellable_input(prompt: str, cancellation_token: Optional[CancellationToken]) -> str:
    task: asyncio.Task[str] = asyncio.create_task(asyncio.to_thread(input, prompt))
    if cancellation_token is not None:
        cancellation_token.link_future(task)
    return await task


def main() -> None:
    """
    Command-line interface for running a complex task using MagenticOne.

    This script accepts a single task string and an optional flag to disable
    human-in-the-loop mode and enable rich console output. It initializes the
    necessary clients and runs the task using the MagenticOne class.

    Arguments:
    task (str): The task to be executed by MagenticOne.
    --no-hil: Optional flag to disable human-in-the-loop mode.
    --rich: Optional flag to enable rich console output.

    Example usage:
    python magentic_one_cli.py "example task"
    python magentic_one_cli.py --no-hil "example task"
    python magentic_one_cli.py --rich "example task"
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run a complex task using MagenticOne.\n\n"
            "For more information, refer to the following paper: https://arxiv.org/abs/2411.04468"
        )
    )
    parser.add_argument("task", type=str, nargs=1, help="The task to be executed by MagenticOne.")
    parser.add_argument("--no-hil", action="store_true", help="Disable human-in-the-loop mode.")
    parser.add_argument(
        "--rich",
        action="store_true",
        help="Enable rich console output",
    )
    args = parser.parse_args()

    async def run_task(task: str, hil_mode: bool, use_rich_console: bool) -> None:
        input_manager = UserInputManager(callback=cancellable_input)
        client = OpenAIChatCompletionClient(model="gpt-4o")
        m1 = MagenticOne(client=client, hil_mode=hil_mode, input_func=input_manager.get_wrapped_callback())

        if use_rich_console:
            await RichConsole(m1.run_stream(task=task), output_stats=False, user_input_manager=input_manager)
        else:
            await Console(m1.run_stream(task=task), output_stats=False, user_input_manager=input_manager)

    task = args.task[0]
    asyncio.run(run_task(task, not args.no_hil, args.rich))


if __name__ == "__main__":
    main()
