import os
import subprocess
import sys
from rich.theme import Theme

os.environ["TOKENIZERS_PARALLELISM"] = "false"  # disable parallelism to avoid warning

custom_theme = Theme(
    {
        "header": "bold",
        "thinking": "italic yellow",
        "acting": "italic red",
        "prompt": "italic",
        "observe": "italic",
        "success": "bold green",
    }
)

def get_repo_root() -> str:
    try:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("Error: not a git repository.")
        sys.exit(1)


def get_gitty_dir() -> str:
    """Get the .gitty directory in the repository root. Create it if it doesn't exist."""
    repo_root = get_repo_root()
    gitty_dir = os.path.join(repo_root, ".gitty")
    if not os.path.exists(gitty_dir):
        os.makedirs(gitty_dir)
    return gitty_dir
