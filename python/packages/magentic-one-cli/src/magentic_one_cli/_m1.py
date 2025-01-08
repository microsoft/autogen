import argparse
import asyncio
import warnings

from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne

# Suppress warnings about the requests.Session() not being closed
warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)


def main() -> None:
    """
    Command-line interface for running a complex task using MagenticOne.

    This script accepts a single task string and an optional flag to disable
    human-in-the-loop mode. It initializes the necessary clients and runs the
    task using the MagenticOne class.

    Arguments:
    task (str): The task to be executed by MagenticOne.
    --no-hil: Optional flag to disable human-in-the-loop mode.

    Example usage:
    python magentic_one_cli.py "example task"
    python magentic_one_cli.py --no-hil "example task"
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run a complex task using MagenticOne.\n\n"
            "For more information, refer to the following paper: https://arxiv.org/abs/2411.04468"
        )
    )
    parser.add_argument("task", type=str, nargs=1, help="The task to be executed by MagenticOne.")
    parser.add_argument("--no-hil", action="store_true", help="Disable human-in-the-loop mode.")
    args = parser.parse_args()

    async def run_task(task: str, hil_mode: bool) -> None:
        client = OpenAIChatCompletionClient(model="gpt-4o")
        m1 = MagenticOne(client=client, hil_mode=hil_mode)
        await Console(m1.run_stream(task=task))

    task = args.task[0]
    asyncio.run(run_task(task, not args.no_hil))


if __name__ == "__main__":
    main()
