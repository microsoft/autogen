import sys
from .run_cmd import run_cli
from .clone_cmd import clone_cli
from .profile_cmd import profile_cli


def main(cli_args=None):
    if cli_args is None:
        cli_args = sys.argv[1:]

    invocation_cmd = "autogenbench"

    commands = [
        {
            "command": "clone",
            "description": "download and expand a benchmark",
            "function": clone_cli,
        },
        {
            "command": "run",
            "description": "run a given benchmark configuration",
            "function": run_cli,
        },
        {
            "command": "profile",
            "description": "run the profiler on previously computed run logs",
            "function": profile_cli,
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
usage: {invocation_cmd} COMMAND ARGS

Where, COMMAND is one of: {commands_list}

and ARGS are specific to the command.
(use '{invocation_cmd} COMMAND --help' for command-specific help)
""".strip()

    help_text = f"""
usage: {invocation_cmd} COMMAND ARGS

{invocation_cmd} is a tool for running and managing AutoGen benchmark scenarios. A typically session might resemble:

    {invocation_cmd} clone HumanEval
    cd HumanEval
    {invocation_cmd} run Tasks/human_eval_two_agents_gpt4.jsonl

which will download the HumanEval benchmark, expand it, and then run the benchmark once with the `human_eval_two_agents_gpt4` configutation.

Available COMMANDs include:

{commands_details}

Additionally, you can use the --help option with any command for further command-specific instructions. E.g.,

    {invocation_cmd} run --help
    {invocation_cmd} clone --help

""".strip()

    if len(cli_args) == 0:
        sys.stderr.write(usage_text + "\n")
        sys.exit(2)

    for command in commands:
        if cli_args[0].lower() == command["command"]:
            if command["function"] is None:
                sys.stderr.write(help_text + "\n")
                sys.exit(0)
            else:
                command["function"](
                    invocation_cmd=invocation_cmd + " " + command["command"],
                    cli_args=cli_args[1:],
                )
                sys.exit(0)

    # Command not found
    sys.stderr.write(f"Invlaid command '{cli_args[0]}'. Available command include: {commands_list}\n")
    sys.exit(2)


###############################################################################
if __name__ == "__main__":
    main()
