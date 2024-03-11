# Will return the filename relative to the workspace path
from pathlib import Path
from typing import Optional
from .base import CommandLineCodeResult


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
        try:
            relative = path.relative_to(workspace_path)
            return str(relative)

        except ValueError:
            return CommandLineCodeResult(exit_code=1, output="Filename is not in the workspace")

    return None
