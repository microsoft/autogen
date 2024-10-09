import sys
from typing import Callable, List, Optional, Sequence

from typing_extensions import TypedDict

from .run_cmd import run_cli
from .tabulate_cmd import tabulate_cli
from .version import __version__


class CommandSpec(TypedDict):
    command: str
    description: str
    function: Optional[Callable[[Sequence[str]], None]]


def main(args: Optional[List[str]] = None) -> None:
    if args is None:
        args = sys.argv[:]  # Shallow copy

    invocation_cmd = "autogenbench"
    version_string = f"AutoGenBench version {__version__}"

    commands: List[CommandSpec] = [
        {
            "command": "run",
            "description": "run a given benchmark configuration",
            "function": run_cli,
        },
        {
            "command": "tabulate",
            "description": "tabulate the results of a previous run",
            "function": tabulate_cli,
        },
        {
            "command": "--version",
            "description": f"print the version of {invocation_cmd}",
            "function": lambda _args: print(f"{version_string}"),
        },
        {"command": "--help", "description": "print this message", "function": None},
    ]

    # Some help string formatting
    commands_list = ", ".join(["'" + c["command"] + "'" for c in commands])
    max_command_len = max([len(c["command"]) for c in commands])
    commands_details = ""
    for c in commands:
        padded_cmd = c["command"]
        while len(padded_cmd) < max_command_len:
            padded_cmd = " " + padded_cmd
        commands_details += f"    {padded_cmd}: {c['description']}\n"

    usage_text = f"""
{version_string}

usage: {invocation_cmd} COMMAND ARGS

Where, COMMAND is one of: {commands_list}

and ARGS are specific to the command.
(use '{invocation_cmd} COMMAND --help' for command-specific help)
""".strip()

    help_text = f"""
{version_string}

usage: {invocation_cmd} COMMAND ARGS

{invocation_cmd} is a tool for running and managing AutoGen benchmark scenarios. A typically session might resemble:

    {invocation_cmd} clone HumanEval
    cd HumanEval
    {invocation_cmd} run Tasks/human_eval_two_agents_gpt4.jsonl

which will download the HumanEval benchmark, expand it, and then run the benchmark once with the `human_eval_two_agents_gpt4` configuration.

Available COMMANDs include:

{commands_details}

Additionally, you can use the --help option with any command for further command-specific instructions. E.g.,

    {invocation_cmd} run --help
    {invocation_cmd} clone --help

""".strip()

    if len(args) < 2:
        sys.stderr.write(usage_text + "\n")
        sys.exit(2)

    for command in commands:
        if args[1].lower() == command["command"]:
            if command["function"] is None:
                sys.stderr.write(help_text + "\n")
                sys.exit(0)
            else:
                command["function"]([invocation_cmd + " " + command["command"]] + args[2:])
                sys.exit(0)

    # Command not found
    sys.stderr.write(f"Invalid command '{args[1]}'. Available commands include: {commands_list}\n")
    sys.exit(2)


###############################################################################
if __name__ == "__main__":
    main()
