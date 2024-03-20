# Will return the filename relative to the workspace path
import re
from pathlib import Path
from typing import Optional


# Raises ValueError if the file is not in the workspace
def _get_file_name_from_content(code: str, workspace_path: Path) -> Optional[str]:
    first_line = code.split("\n")[0]
    # TODO - support other languages
    if first_line.startswith("# filename:"):
        filename = first_line.split(":")[1].strip()

        # Handle relative paths in the filename
        path = Path(filename)
        if not path.is_absolute():
            path = workspace_path / path
        path = path.resolve()
        # Throws an error if the file is not in the workspace
        relative = path.relative_to(workspace_path.resolve())
        return str(relative)

    return None


def silence_pip(code: str, lang: str) -> str:
    """Apply -qqq flag to pip install commands."""
    if lang == "python":
        regex = r"^! ?pip install"
    elif lang in ["bash", "shell", "sh", "pwsh", "powershell", "ps1"]:
        regex = r"^pip install"
    else:
        return code

    # Find lines that start with pip install and make sure "-qqq" flag is added.
    lines = code.split("\n")
    for i, line in enumerate(lines):
        # use regex to find lines that start with pip install.
        match = re.search(regex, line)
        if match is not None:
            if "-qqq" not in line:
                lines[i] = line.replace(match.group(0), match.group(0) + " -qqq")
    return "\n".join(lines)
