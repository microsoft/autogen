import argparse
import asyncio
import os
import subprocess
import sys
from rich.console import Console

from ._gitty import (
    gitty,
    fetch_and_update_issues,
    get_gitty_dir,
    edit_config_file,
    check_gh_cli,
    check_openai_key,
)

console = Console()

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gitty: A GitHub Issue/PR Assistant.\n\n"
        "This tool fetches GitHub issues or pull requests and uses an AI assistant to generate concise,\n"
        "technical responses to help make progress on your project. You can specify a repository using --repo\n"
        "or let the tool auto-detect the repository based on the current directory.",
        epilog="Subcommands:\n  issue - Process and respond to GitHub issues\n  pr    - Process and respond to GitHub pull requests\n  local - Edit repo-specific gitty config\n  global- Edit global gitty config\n\n"
        "Usage examples:\n  gitty issue 123\n  gitty pr 456\n  gitty local\n  gitty global",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "command", choices=["issue", "pr", "fetch", "local", "global"], nargs="?", help="Command to execute"
    )
    parser.add_argument("number", type=int, nargs="?", help="Issue or PR number (if applicable)")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    command = args.command

    # Check for gh CLI installation before processing commands that need it
    if command in ["issue", "pr", "fetch"]:
        check_gh_cli()

    # Check for OpenAI API key before processing commands that need it
    if command in ["issue", "pr"]:
        check_openai_key()

    if command in ["issue", "pr"]:
        # Always auto-detect repository
        pipe = subprocess.run(
            [
                "gh",
                "repo",
                "view",
                "--json",
                "owner,name",
                "-q",
                '.owner.login + "/" + .name',
            ],
            check=True,
            capture_output=True,
        )
        owner, repo = pipe.stdout.decode().strip().split("/")
        number = args.number
        if command == "issue":
            asyncio.run(gitty(owner, repo, command, number))
        else:
            console.print(f"Command '{command}' is not implemented.")
            sys.exit(1)
    elif command == "fetch":
        pipe = subprocess.run(
            [
                "gh",
                "repo",
                "view",
                "--json",
                "owner,name",
                "-q",
                '.owner.login + "/" + .name',
            ],
            check=True,
            capture_output=True,
        )
        owner, repo = pipe.stdout.decode().strip().split("/")
        gitty_dir = get_gitty_dir()
        db_path = os.path.join(gitty_dir, "issues.db")
        fetch_and_update_issues(owner, repo, db_path)
    elif command == "local":
        gitty_dir = get_gitty_dir()
        local_config_path = os.path.join(gitty_dir, "config")
        edit_config_file(local_config_path)
    elif command == "global":
        global_config_dir = os.path.expanduser("~/.gitty")
        os.makedirs(global_config_dir, exist_ok=True)
        global_config_path = os.path.join(global_config_dir, "config")
        edit_config_file(global_config_path)

if __name__ == "__main__":
    main()
