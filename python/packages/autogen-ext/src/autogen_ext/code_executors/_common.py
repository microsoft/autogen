import inspect
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent, indent
from typing import Any, Callable, Optional, Sequence, Set, TypeVar, Union

from autogen_core.code_executor import Alias, CodeResult, FunctionWithRequirements, FunctionWithRequirementsStr, Import
from typing_extensions import ParamSpec


@dataclass
class CommandLineCodeResult(CodeResult):
    """A code result class for command line code executor."""

    code_file: Optional[str]


T = TypeVar("T")
P = ParamSpec("P")


def _to_code(func: Union[FunctionWithRequirements[T, P], Callable[P, T], FunctionWithRequirementsStr]) -> str:
    if isinstance(func, FunctionWithRequirementsStr):
        return func.func

    code = inspect.getsource(func)
    # Strip the decorator
    if code.startswith("@"):
        code = code[code.index("\n") + 1 :]
    return code


def _import_to_str(im: Import) -> str:
    if isinstance(im, str):
        return f"import {im}"
    elif isinstance(im, Alias):
        return f"import {im.name} as {im.alias}"
    else:

        def to_str(i: Union[str, Alias]) -> str:
            if isinstance(i, str):
                return i
            else:
                return f"{i.name} as {i.alias}"

        imports = ", ".join(map(to_str, im.imports))
        return f"from {im.module} import {imports}"


def build_python_functions_file(
    funcs: Sequence[Union[FunctionWithRequirements[Any, P], Callable[..., Any], FunctionWithRequirementsStr]],
) -> str:
    """:meta private:"""
    # First collect all global imports
    global_imports: Set[Import] = set()
    for func in funcs:
        if isinstance(func, (FunctionWithRequirements, FunctionWithRequirementsStr)):
            global_imports.update(func.global_imports)

    content = "\n".join(map(_import_to_str, global_imports)) + "\n\n"

    for func in funcs:
        content += _to_code(func) + "\n\n"

    return content


def to_stub(func: Union[Callable[..., Any], FunctionWithRequirementsStr]) -> str:
    """Generate a stub for a function as a string

    Args:
        func (Callable[..., Any]): The function to generate a stub for

    Returns:
        str: The stub for the function
    """
    if isinstance(func, FunctionWithRequirementsStr):
        return to_stub(func.compiled_func)

    content = f"def {func.__name__}{inspect.signature(func)}:\n"
    docstring = func.__doc__

    if docstring:
        docstring = dedent(docstring)
        docstring = '"""' + docstring + '"""'
        docstring = indent(docstring, "    ")
        content += docstring + "\n"

    content += "    ..."
    return content


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
    if lang in ["pwsh", "powershell", "ps1"]:
        # Check if pwsh is available, otherwise fall back to powershell
        if shutil.which("pwsh") is not None:
            return "pwsh"
        elif shutil.which("powershell") is not None:
            return "powershell"
        else:
            raise ValueError("Powershell or pwsh is not installed. Please install one of them.")
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
