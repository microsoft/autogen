#!/usr/bin/env python

from __future__ import annotations
import signal
import sys
from pathlib import Path
import subprocess
import argparse
import shutil
import json
import tempfile
import threading
import time
import typing
import concurrent.futures
import os
from typing import Dict, Optional, Tuple, Union
from dataclasses import dataclass
from multiprocessing import current_process
from termcolor import colored

try:
    import yaml
except ImportError:
    print("pyyaml not found.\n\nPlease install pyyaml:\n\tpip install pyyaml\n")
    sys.exit(1)

try:
    import nbclient
    from nbclient.client import (
        CellExecutionError,
        CellTimeoutError,
        NotebookClient,
    )
except ImportError:
    if current_process().name == "MainProcess":
        print("nbclient not found.\n\nPlease install nbclient:\n\tpip install nbclient\n")
        print("test won't work without nbclient")

try:
    import nbformat
    from nbformat import NotebookNode
except ImportError:
    if current_process().name == "MainProcess":
        print("nbformat not found.\n\nPlease install nbformat:\n\tpip install nbformat\n")
        print("test won't work without nbclient")


class Result:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def check_quarto_bin(quarto_bin: str = "quarto") -> None:
    """Check if quarto is installed."""
    try:
        version = subprocess.check_output([quarto_bin, "--version"], text=True).strip()
        version = tuple(map(int, version.split(".")))
        if version < (1, 5, 23):
            print("Quarto version is too old. Please upgrade to 1.5.23 or later.")
            sys.exit(1)

    except FileNotFoundError:
        print("Quarto is not installed. Please install it from https://quarto.org")
        sys.exit(1)


def notebooks_target_dir(website_directory: Path) -> Path:
    """Return the target directory for notebooks."""
    return website_directory / "docs" / "notebooks"


def load_metadata(notebook: Path) -> typing.Dict:
    content = json.load(notebook.open())
    return content["metadata"]


def skip_reason_or_none_if_ok(notebook: Path) -> typing.Optional[str]:
    """Return a reason to skip the notebook, or None if it should not be skipped."""

    if notebook.suffix != ".ipynb":
        return "not a notebook"

    if not notebook.exists():
        return "file does not exist"

    # Extra checks for notebooks in the notebook directory
    if "notebook" not in notebook.parts:
        return None

    with open(notebook, "r", encoding="utf-8") as f:
        content = f.read()

    # Load the json and get the first cell
    json_content = json.loads(content)
    first_cell = json_content["cells"][0]

    # <!-- and --> must exists on lines on their own
    if first_cell["cell_type"] == "markdown" and first_cell["source"][0].strip() == "<!--":
        raise ValueError(
            f"Error in {str(notebook.resolve())} - Front matter should be defined in the notebook metadata now."
        )

    metadata = load_metadata(notebook)

    if "skip_render" in metadata:
        return metadata["skip_render"]

    if "front_matter" not in metadata:
        return "front matter missing from notebook metadata ⚠️"

    front_matter = metadata["front_matter"]

    if "tags" not in front_matter:
        return "tags is not in front matter"

    if "description" not in front_matter:
        return "description is not in front matter"

    # Make sure tags is a list of strings
    if not all([isinstance(tag, str) for tag in front_matter["tags"]]):
        return "tags must be a list of strings"

    # Make sure description is a string
    if not isinstance(front_matter["description"], str):
        return "description must be a string"

    return None


def extract_title(notebook: Path) -> Optional[str]:
    """Extract the title of the notebook."""
    with open(notebook, "r", encoding="utf-8") as f:
        content = f.read()

    # Load the json and get the first cell
    json_content = json.loads(content)
    first_cell = json_content["cells"][0]

    # find the # title
    for line in first_cell["source"]:
        if line.startswith("# "):
            title = line[2:].strip()
            # Strip off the { if it exists
            if "{" in title:
                title = title[: title.find("{")].strip()
            return title

    return None


def process_notebook(src_notebook: Path, website_dir: Path, notebook_dir: Path, quarto_bin: str, dry_run: bool) -> str:
    """Process a single notebook."""

    in_notebook_dir = "notebook" in src_notebook.parts

    metadata = load_metadata(src_notebook)

    title = extract_title(src_notebook)
    if title is None:
        return fmt_error(src_notebook, "Title not found in notebook")

    front_matter = {}
    if "front_matter" in metadata:
        front_matter = metadata["front_matter"]

    front_matter["title"] = title

    if in_notebook_dir:
        relative_notebook = src_notebook.resolve().relative_to(notebook_dir.resolve())
        dest_dir = notebooks_target_dir(website_directory=website_dir)
        target_file = dest_dir / relative_notebook.with_suffix(".mdx")
        intermediate_notebook = dest_dir / relative_notebook

        # If the intermediate_notebook already exists, check if it is newer than the source file
        if target_file.exists():
            if target_file.stat().st_mtime > src_notebook.stat().st_mtime:
                return fmt_skip(src_notebook, f"target file ({target_file.name}) is newer ☑️")

        if dry_run:
            return colored(f"Would process {src_notebook.name}", "green")

        # Copy notebook to target dir
        # The reason we copy the notebook is that quarto does not support rendering from a different directory
        shutil.copy(src_notebook, intermediate_notebook)

        # Check if another file has to be copied too
        # Solely added for the purpose of agent_library_example.json
        if "extra_files_to_copy" in metadata:
            for file in metadata["extra_files_to_copy"]:
                shutil.copy(src_notebook.parent / file, dest_dir / file)

        # Capture output
        result = subprocess.run(
            [quarto_bin, "render", intermediate_notebook], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode != 0:
            return fmt_error(
                src_notebook, f"Failed to render {src_notebook}\n\nstderr:\n{result.stderr}\nstdout:\n{result.stdout}"
            )

        # Unlink intermediate files
        intermediate_notebook.unlink()
    else:
        target_file = src_notebook.with_suffix(".mdx")

        # If the intermediate_notebook already exists, check if it is newer than the source file
        if target_file.exists():
            if target_file.stat().st_mtime > src_notebook.stat().st_mtime:
                return fmt_skip(src_notebook, f"target file ({target_file.name}) is newer ☑️")

        if dry_run:
            return colored(f"Would process {src_notebook.name}", "green")

        result = subprocess.run(
            [quarto_bin, "render", src_notebook], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode != 0:
            return fmt_error(
                src_notebook, f"Failed to render {src_notebook}\n\nstderr:\n{result.stderr}\nstdout:\n{result.stdout}"
            )

    post_process_mdx(target_file, src_notebook, front_matter)

    return fmt_ok(src_notebook)


# Notebook execution based on nbmake: https://github.com/treebeardtech/nbmakes
@dataclass
class NotebookError:
    error_name: str
    error_value: Optional[str]
    traceback: str
    cell_source: str


@dataclass
class NotebookSkip:
    reason: str


NB_VERSION = 4


def test_notebook(notebook_path: Path, timeout: int = 300) -> Tuple[Path, Optional[Union[NotebookError, NotebookSkip]]]:
    nb = nbformat.read(str(notebook_path), NB_VERSION)

    if "skip_test" in nb.metadata:
        return notebook_path, NotebookSkip(reason=nb.metadata.skip_test)

    try:
        c = NotebookClient(
            nb,
            timeout=timeout,
            allow_errors=False,
            record_timing=True,
        )
        os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        with tempfile.TemporaryDirectory() as tempdir:
            c.execute(cwd=tempdir)
    except CellExecutionError:
        error = get_error_info(nb)
        assert error is not None
        return notebook_path, error
    except CellTimeoutError:
        error = get_timeout_info(nb)
        assert error is not None
        return notebook_path, error

    return notebook_path, None


# Find the first code cell which did not complete.
def get_timeout_info(
    nb: NotebookNode,
) -> Optional[NotebookError]:
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        if "shell.execute_reply" not in cell.metadata.execution:
            return NotebookError(
                error_name="timeout",
                error_value="",
                traceback="",
                cell_source="".join(cell["source"]),
            )

    return None


def get_error_info(nb: NotebookNode) -> Optional[NotebookError]:
    for cell in nb["cells"]:  # get LAST error
        if cell["cell_type"] != "code":
            continue
        errors = [output for output in cell["outputs"] if output["output_type"] == "error" or "ename" in output]

        if errors:
            traceback = "\n".join(errors[0].get("traceback", ""))
            return NotebookError(
                error_name=errors[0].get("ename", ""),
                error_value=errors[0].get("evalue", ""),
                traceback=traceback,
                cell_source="".join(cell["source"]),
            )
    return None


# rendered_notebook is the final mdx file
def post_process_mdx(rendered_mdx: Path, source_notebooks: Path, front_matter: Dict) -> None:
    with open(rendered_mdx, "r", encoding="utf-8") as f:
        content = f.read()

    # If there is front matter in the mdx file, we need to remove it
    if content.startswith("---"):
        front_matter_end = content.find("---", 3)
        front_matter = yaml.safe_load(content[4:front_matter_end])
        content = content[front_matter_end + 3 :]

    # Each intermediate path needs to be resolved for this to work reliably
    repo_root = Path(__file__).parent.resolve().parent.resolve()
    repo_relative_notebook = source_notebooks.resolve().relative_to(repo_root)
    front_matter["source_notebook"] = f"/{repo_relative_notebook}"
    front_matter["custom_edit_url"] = f"https://github.com/microsoft/autogen/edit/main/{repo_relative_notebook}"

    # Is there a title on the content? Only search up until the first code cell
    first_code_cell = content.find("```")
    if first_code_cell != -1:
        title_search_content = content[:first_code_cell]
    else:
        title_search_content = content

    title_exists = title_search_content.find("\n# ") != -1
    if not title_exists:
        content = f"# {front_matter['title']}\n{content}"

    # inject in content directly after the markdown title the word done
    # Find the end of the line with the title
    title_end = content.find("\n", content.find("#"))

    # Extract page title
    title = content[content.find("#") + 1 : content.find("\n", content.find("#"))].strip()
    # If there is a { in the title we trim off the { and everything after it
    if "{" in title:
        title = title[: title.find("{")].strip()

    github_link = f"https://github.com/microsoft/autogen/blob/main/{repo_relative_notebook}"
    content = (
        content[:title_end]
        + "\n[![Open on GitHub](https://img.shields.io/badge/Open%20on%20GitHub-grey?logo=github)]("
        + github_link
        + ")"
        + content[title_end:]
    )

    # If no colab link is present, insert one
    if "colab-badge.svg" not in content:
        colab_link = f"https://colab.research.google.com/github/microsoft/autogen/blob/main/{repo_relative_notebook}"
        content = (
            content[:title_end]
            + "\n[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]("
            + colab_link
            + ")"
            + content[title_end:]
        )

    # Dump front_matter to ysaml
    front_matter = yaml.dump(front_matter, default_flow_style=False)

    # Rewrite the content as
    # ---
    # front_matter
    # ---
    # content
    new_content = f"---\n{front_matter}---\n{content}"
    with open(rendered_mdx, "w", encoding="utf-8") as f:
        f.write(new_content)


def path(path_str: str) -> Path:
    """Return a Path object."""
    return Path(path_str)


def collect_notebooks(notebook_directory: Path, website_directory: Path) -> typing.List[Path]:
    notebooks = list(notebook_directory.glob("*.ipynb"))
    notebooks.extend(list(website_directory.glob("docs/**/*.ipynb")))
    return notebooks


def fmt_skip(notebook: Path, reason: str) -> str:
    return f"{colored('[Skip]', 'yellow')} {colored(notebook.name, 'blue')}: {reason}"


def fmt_ok(notebook: Path) -> str:
    return f"{colored('[OK]', 'green')} {colored(notebook.name, 'blue')} ✅"


def fmt_error(notebook: Path, error: Union[NotebookError, str]) -> str:
    if isinstance(error, str):
        return f"{colored('[Error]', 'red')} {colored(notebook.name, 'blue')}: {error}"
    elif isinstance(error, NotebookError):
        return f"{colored('[Error]', 'red')} {colored(notebook.name, 'blue')}: {error.error_name} - {error.error_value}"
    else:
        raise ValueError("error must be a string or a NotebookError")


def start_thread_to_terminate_when_parent_process_dies(ppid: int):
    pid = os.getpid()

    def f() -> None:
        while True:
            try:
                os.kill(ppid, 0)
            except OSError:
                os.kill(pid, signal.SIGTERM)
            time.sleep(1)

    thread = threading.Thread(target=f, daemon=True)
    thread.start()


def main() -> None:
    script_dir = Path(__file__).parent.absolute()
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand")

    parser.add_argument(
        "--notebook-directory",
        type=path,
        help="Directory containing notebooks to process",
        default=script_dir / "../notebook",
    )
    parser.add_argument(
        "--website-directory", type=path, help="Root directory of docusarus website", default=script_dir
    )

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--quarto-bin", help="Path to quarto binary", default="quarto")
    render_parser.add_argument("--dry-run", help="Don't render", action="store_true")
    render_parser.add_argument("notebooks", type=path, nargs="*", default=None)

    test_parser = subparsers.add_parser("test")
    test_parser.add_argument("--timeout", help="Timeout for each notebook", type=int, default=60)
    test_parser.add_argument("--exit-on-first-fail", "-e", help="Exit after first test fail", action="store_true")
    test_parser.add_argument("notebooks", type=path, nargs="*", default=None)
    test_parser.add_argument("--workers", help="Number of workers to use", type=int, default=-1)

    args = parser.parse_args()

    if args.subcommand is None:
        print("No subcommand specified")
        sys.exit(1)

    if args.notebooks:
        collected_notebooks = args.notebooks
    else:
        collected_notebooks = collect_notebooks(args.notebook_directory, args.website_directory)

    filtered_notebooks = []
    for notebook in collected_notebooks:
        reason = skip_reason_or_none_if_ok(notebook)
        if reason:
            print(fmt_skip(notebook, reason))
        else:
            filtered_notebooks.append(notebook)

    if args.subcommand == "test":
        if args.workers == -1:
            args.workers = None
        failure = False
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=args.workers,
            initializer=start_thread_to_terminate_when_parent_process_dies,
            initargs=(os.getpid(),),
        ) as executor:
            futures = [executor.submit(test_notebook, f, args.timeout) for f in filtered_notebooks]
            for future in concurrent.futures.as_completed(futures):
                notebook, optional_error_or_skip = future.result()
                if isinstance(optional_error_or_skip, NotebookError):
                    if optional_error_or_skip.error_name == "timeout":
                        print(fmt_error(notebook, optional_error_or_skip.error_name))

                    else:
                        print("-" * 80)

                        print(fmt_error(notebook, optional_error_or_skip))
                        print(optional_error_or_skip.traceback)
                        print("-" * 80)
                    if args.exit_on_first_fail:
                        sys.exit(1)
                    failure = True
                elif isinstance(optional_error_or_skip, NotebookSkip):
                    print(fmt_skip(notebook, optional_error_or_skip.reason))
                else:
                    print(fmt_ok(notebook))

        if failure:
            sys.exit(1)

    elif args.subcommand == "render":
        check_quarto_bin(args.quarto_bin)

        if not notebooks_target_dir(args.website_directory).exists():
            notebooks_target_dir(args.website_directory).mkdir(parents=True)

        for notebook in filtered_notebooks:
            print(
                process_notebook(
                    notebook, args.website_directory, args.notebook_directory, args.quarto_bin, args.dry_run
                )
            )
    else:
        print("Unknown subcommand")
        sys.exit(1)


if __name__ == "__main__":
    main()
