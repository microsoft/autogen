import asyncio
import argparse
import shlex
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_agentchat.ui import Console

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run a complex task using MagenticOne.\n\n"
            "For more information, refer to the following paper: https://arxiv.org/abs/2411.04468"
        )
    )
    parser.add_argument('task', type=str, nargs='*', help='The task to be executed by MagenticOne.')
    parser.add_argument('--no-hil', action='store_true', help='Disable human-in-the-loop mode.')
    args = parser.parse_args()

    async def run_task(task, hil_mode):
        client = OpenAIChatCompletionClient(model="gpt-4o")
        m1 = MagenticOne(client=client, hil_mode=hil_mode)
        await Console(m1.run_stream(task=task))

    task = ' '.join(shlex.split(' '.join(args.task)))
    asyncio.run(run_task(task, not args.no_hil))

if __name__ == "__main__":
    main()
