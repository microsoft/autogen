# File based from: https://github.com/microsoft/autogen/blob/main/autogen/coding/utils.py
# Credit to original authors

# Will return the filename relative to the workspace path
import re
import venv
from pathlib import Path
from types import SimpleNamespace
from typing import Optional


# Raises ValueError if the file is not in the workspace
def get_file_name_from_content(code: str, workspace_path: Path) -> Optional[str]:
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


def get_required_packages(code: str, lang: str) -> set[str]:
    ret: set[str] = set()
    if lang == "python":
        regex = r"^! ?pip install(.*)$"
    else:
        return ret

    # Find lines that start with pip install and make sure "-qqq" flag is added.
    lines = code.split("\n")
    for _, line in enumerate(lines):
        # use regex to find lines that start with pip install.
        match = re.search(regex, line)
        if match is not None:
            reqs = match.group(1).split(",")
            ret = {req.strip(" ") for req in reqs}
    return ret


PYTHON_VARIANTS = ["python", "Python", "py"]


def lang_to_cmd(lang: str) -> str:
    if lang in PYTHON_VARIANTS:
        return "python"
    if lang.startswith("python") or lang in ["bash", "sh"]:
        return lang
    if lang in ["shell"]:
        return "sh"
    else:
        raise ValueError(f"Unsupported language: {lang}")


# Regular expression for finding a code block
# ```[ \t]*(\w+)?[ \t]*\r?\n(.*?)[ \t]*\r?\n``` Matches multi-line code blocks.
#   The [ \t]* matches the potential spaces before language name.
#   The (\w+)? matches the language, where the ? indicates it is optional.
#   The [ \t]* matches the potential spaces (not newlines) after language name.
#   The \r?\n makes sure there is a linebreak after ```.
#   The (.*?) matches the code itself (non-greedy).
#   The \r?\n makes sure there is a linebreak before ```.
#   The [ \t]* matches the potential spaces before closing ``` (the spec allows indentation).
CODE_BLOCK_PATTERN = r"```[ \t]*(\w+)?[ \t]*\r?\n(.*?)\r?\n[ \t]*```"


def infer_lang(code: str) -> str:
    """infer the language for the code.
    TODO: make it robust.
    """
    if code.startswith("python ") or code.startswith("pip") or code.startswith("python3 "):
        return "sh"

    # check if code is a valid python code
    try:
        compile(code, "test", "exec")
        return "python"
    except SyntaxError:
        # not a valid python code
        return "unknown"


def create_virtual_env(
    dir_path: str,
    system_site_packages: bool = False,
    clear: bool = False,
    symlinks: bool = False,
    upgrade: bool = False,
    with_pip: bool = True,
    prompt: Optional[str] = None,
    upgrade_deps: bool = False,
) -> SimpleNamespace:
    """Creates a python virtual environment and returns the context.

    Args:
        dir_path: The directory path where the virtual environment will be created
        system_site_packages: If True, the system (global) site-packages
                                    dir is available to created environments.
        clear: If True, delete the contents of the environment directory if
                    it already exists, before environment creation.
        symlinks: If True, attempt to symlink rather than copy files into
                        virtual environment.
        upgrade: If True, upgrade an existing virtual environment.
        with_pip: If True, ensure pip is installed in the virtual
                        environment
        prompt: Alternative terminal prefix for the environment.
        upgrade_deps: Update the base venv modules to the latest on PyPI

    Returns:
        Context for the virtual environment.
    """
    env_builder = venv.EnvBuilder(
        system_site_packages=system_site_packages,
        clear=clear,
        symlinks=symlinks,
        upgrade=upgrade,
        with_pip=with_pip,
        prompt=prompt,
        upgrade_deps=upgrade_deps,
    )

    env_builder.create(dir_path)
    return env_builder.ensure_directories(dir_path)
