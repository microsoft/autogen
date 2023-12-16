import sys
from .run_cmd import run_cli
from .clone_cmd import clone_cli


def main(cli_args=None):
    # Get the args
    if cli_args is None:
        cli_args = sys.argv

    # Figure out how the script was invoked
    invocation_cmd = "autogenbench"
    try:
        import psutil
        import os

        process = psutil.Process(os.getpid())  # get the process object
        full_argv = process.cmdline()
        cmd_argv = full_argv[0 : len(full_argv) - len(sys.argv) + 1]
        invocation_cmd = " ".join(cmd_argv)
    except ModuleNotFoundError:
        pass

    # We want to support multiple subcommands like:
    #   autogenbench run
    #   autogenbench report
    # Etc.
    #
    # With 'run' being the default.
    #
    # We set up that structure here, for future use
    if len(cli_args) < 2:
        run_cli(invocation_cmd=invocation_cmd, cli_args=[])
    elif cli_args[1] == "run":
        run_cli(invocation_cmd=invocation_cmd + " run", cli_args=cli_args[2:])
    elif cli_args[1] == "clone":
        clone_cli(invocation_cmd=invocation_cmd + " run", cli_args=cli_args[2:])
    elif cli_args[1] == "help":
        run_cli(invocation_cmd=invocation_cmd, cli_args=["--help"])
    else:
        run_cli(invocation_cmd=invocation_cmd, cli_args=cli_args[1:])


###############################################################################
if __name__ == "__main__":
    main()
