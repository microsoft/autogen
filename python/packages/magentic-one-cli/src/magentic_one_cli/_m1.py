import argparse
import asyncio
import os
import sys
import warnings
from typing import Any, Dict, Optional

import yaml
from autogen_agentchat.ui import Console, UserInputManager
from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_ext.ui import RichConsole

# Suppress warnings about the requests.Session() not being closed
warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)

DEFAULT_CONFIG_FILE = "config.yaml"
DEFAULT_CONFIG_CONTENTS = """# config.yaml
#

client:
  provider: autogen_ext.models.openai.OpenAIChatCompletionClient
  config:
    model: gpt-4o
"""


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
    --config: Optional flag to specify an alternate model configuration

    Example usage:
    python magentic_one_cli.py "example task"
    python magentic_one_cli.py --no-hil "example task"
    python magentic_one_cli.py --rich "example task"
    python magentic_one_cli.py --config config.yaml "example task"

    Use --sample-config to print a sample configuration file.

    Example:
    python magentic_one_cli.py --sample-config

    NOTE:
    If --config is not specified, the configuration is loaded from the
    file DEFAULT_CONFIG_FILE. If that file does not exist, load from
    DEFAULT_CONFIG_CONTENTS.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run a complex task using MagenticOne.\n\n"
            "For more information, refer to the following paper: https://arxiv.org/abs/2411.04468"
        )
    )
    parser.add_argument("task", type=str, nargs="?", help="The task to be executed by MagenticOne.")
    parser.add_argument("--no-hil", action="store_true", help="Disable human-in-the-loop mode.")
    parser.add_argument(
        "--rich",
        action="store_true",
        help="Enable rich console output",
    )
    parser.add_argument(
        "--config",
        type=str,
        nargs=1,
        help="The model configuration file to use. Leave empty to print a sample configuration.",
    )
    parser.add_argument("--sample-config", action="store_true", help="Print a sample configuration to console.")

    args = parser.parse_args()

    if args.sample_config:
        sys.stdout.write(DEFAULT_CONFIG_CONTENTS + "\n")
        return

    # We're not printing a sample, so we need a task
    if args.task is None:
        parser.print_usage()
        return

    # Load the configuration
    config: Dict[str, Any] = {}

    if args.config is None:
        if os.path.isfile(DEFAULT_CONFIG_FILE):
            with open(DEFAULT_CONFIG_FILE, "r") as f:
                config = yaml.safe_load(f)
        else:
            config = yaml.safe_load(DEFAULT_CONFIG_CONTENTS)
    else:
        with open(args.config if isinstance(args.config, str) else args.config[0], "r") as f:
            config = yaml.safe_load(f)

    client = ChatCompletionClient.load_component(config["client"])

    # Run the task
    async def run_task(task: str, hil_mode: bool, use_rich_console: bool) -> None:
        input_manager = UserInputManager(callback=cancellable_input)
        m1 = MagenticOne(client=client, hil_mode=hil_mode, input_func=input_manager.get_wrapped_callback())

        if use_rich_console:
            await RichConsole(m1.run_stream(task=task), output_stats=False, user_input_manager=input_manager)
        else:
            await Console(m1.run_stream(task=task), output_stats=False, user_input_manager=input_manager)

    task = args.task if isinstance(args.task, str) else args.task[0]
    asyncio.run(run_task(task, not args.no_hil, args.rich))


if __name__ == "__main__":
    main()
