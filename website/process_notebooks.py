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

from typing import Optional, Tuple, Union
from dataclasses import dataclass

from multiprocessing import current_process

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


try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


class Result:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def check_quarto_bin(quarto_bin: str = "quarto") -> None:
    """Check if quarto is installed."""
    try:
        subprocess.check_output([quarto_bin, "--version"])
    except FileNotFoundError:
        print("Quarto is not installed. Please install it from https://quarto.org")
        sys.exit(1)


def notebooks_target_dir(website_directory: Path) -> Path:
    """Return the target directory for notebooks."""
    return website_directory / "docs" / "notebooks"


def extract_yaml_from_notebook(notebook: Path) -> typing.Optional[typing.Dict]:
    with open(notebook, "r", encoding="utf-8") as f:
        content = f.read()

    json_content = json.loads(content)
    first_cell = json_content["cells"][0]

    # <!-- and --> must exists on lines on their own
    if first_cell["cell_type"] != "markdown":
        return None

    lines = first_cell["source"]
    if "<!--" != lines[0].strip():
        return None

    # remove trailing whitespace
    lines = [line.rstrip() for line in lines]

    if "-->" not in lines:
        return None

    closing_arrow_idx = lines.index("-->")

    front_matter_lines = lines[1:closing_arrow_idx]
    front_matter = yaml.safe_load("\n".join(front_matter_lines))
    return front_matter


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
    if first_cell["cell_type"] != "markdown":
        return "first cell is not markdown"

    lines = first_cell["source"]
    if "<!--" != lines[0].strip():
        return "first line does not contain only '<!--'"

    # remove trailing whitespace
    lines = [line.rstrip() for line in lines]

    if "-->" not in lines:
        return "no closing --> found, or it is not on a line on its own"

    try:
        front_matter = extract_yaml_from_notebook(notebook)
    except yaml.YAMLError as e:
        return colored(f"Failed to parse front matter in {notebook.name}: {e}", "red")

    # Should not be none at this point as we have already done the same checks as in extract_yaml_from_notebook
    assert front_matter is not None, f"Front matter is None for {notebook.name}"

    if "skip" in front_matter and front_matter["skip"] is True:
        return "skip is set to true"

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


def process_notebook(src_notebook: Path, website_dir: Path, notebook_dir: Path, quarto_bin: str, dry_run: bool) -> str:
    """Process a single notebook."""

    in_notebook_dir = "notebook" in src_notebook.parts

    if in_notebook_dir:
        relative_notebook = src_notebook.relative_to(notebook_dir)
        dest_dir = notebooks_target_dir(website_directory=website_dir)
        target_mdx_file = dest_dir / relative_notebook.with_suffix(".mdx")
        intermediate_notebook = dest_dir / relative_notebook

        # If the intermediate_notebook already exists, check if it is newer than the source file
        if target_mdx_file.exists():
            if target_mdx_file.stat().st_mtime > src_notebook.stat().st_mtime:
                return colored(f"Skipping {src_notebook.name}, as target file is newer", "blue")

        if dry_run:
            return colored(f"Would process {src_notebook.name}", "green")

        # Copy notebook to target dir
        # The reason we copy the notebook is that quarto does not support rendering from a different directory
        shutil.copy(src_notebook, intermediate_notebook)

        # Check if another file has to be copied too
        # Solely added for the purpose of agent_library_example.json
        front_matter = extract_yaml_from_notebook(src_notebook)
        # Should not be none at this point as we have already done the same checks as in extract_yaml_from_notebook
        assert front_matter is not None, f"Front matter is None for {src_notebook.name}"
        if "extra_files_to_copy" in front_matter:
            for file in front_matter["extra_files_to_copy"]:
                shutil.copy(src_notebook.parent / file, dest_dir / file)

        # Capture output
        result = subprocess.run(
            [quarto_bin, "render", intermediate_notebook], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode != 0:
            return (
                colored(f"Failed to render {intermediate_notebook}", "red")
                + f"\n{result.stderr}"
                + f"\n{result.stdout}"
            )

        # Unlink intermediate files
        intermediate_notebook.unlink()

        if "extra_files_to_copy" in front_matter:
            for file in front_matter["extra_files_to_copy"]:
                (dest_dir / file).unlink()

        # Post process the file
        post_process_mdx(target_mdx_file)
    else:
        target_mdx_file = src_notebook.with_suffix(".mdx")

        # If the intermediate_notebook already exists, check if it is newer than the source file
        if target_mdx_file.exists():
            if target_mdx_file.stat().st_mtime > src_notebook.stat().st_mtime:
                return colored(f"Skipping {src_notebook.name}, as target file is newer", "blue")

        if dry_run:
            return colored(f"Would process {src_notebook.name}", "green")

        result = subprocess.run(
            [quarto_bin, "render", src_notebook], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode != 0:
            return colored(f"Failed to render {src_notebook}", "red") + f"\n{result.stderr}" + f"\n{result.stdout}"

    return colored(f"Processed {src_notebook.name}", "green")


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

    allow_errors = False
    if "execution" in nb.metadata:
        if "timeout" in nb.metadata.execution:
            timeout = nb.metadata.execution.timeout
        if "allow_errors" in nb.metadata.execution:
            allow_errors = nb.metadata.execution.allow_errors

    if "test_skip" in nb.metadata:
        return notebook_path, NotebookSkip(reason=nb.metadata.test_skip)

    try:
        c = NotebookClient(
            nb,
            timeout=timeout,
            allow_errors=allow_errors,
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
def post_process_mdx(rendered_mdx: Path) -> None:
    notebook_name = f"{rendered_mdx.stem}.ipynb"
    with open(rendered_mdx, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for existence of "export const quartoRawHtml", this indicates there was a front matter line in the file
    if "export const quartoRawHtml" not in content:
        raise ValueError(f"File {rendered_mdx} does not contain 'export const quartoRawHtml'")

    # Extract the text between <!-- and -->
    front_matter = content.split("<!--")[1].split("-->")[0]
    # Strip empty lines before and after
    front_matter = "\n".join([line for line in front_matter.split("\n") if line.strip() != ""])

    # add file path
    front_matter += f"\nsource_notebook: /notebook/{notebook_name}"
    # Custom edit url
    front_matter += f"\ncustom_edit_url: https://github.com/microsoft/autogen/edit/main/notebook/{notebook_name}"

    # inject in content directly after the markdown title the word done
    # Find the end of the line with the title
    title_end = content.find("\n", content.find("#"))

    # Extract page title
    title = content[content.find("#") + 1 : content.find("\n", content.find("#"))].strip()

    front_matter += f"\ntitle: {title}"

    github_link = f"https://github.com/microsoft/autogen/blob/main/notebook/{notebook_name}"
    content = (
        content[:title_end]
        + "\n[![Open on GitHub](https://img.shields.io/badge/Open%20on%20GitHub-grey?logo=github)]("
        + github_link
        + ")"
        + content[title_end:]
    )

    # If no colab link is present, insert one
    if "colab-badge.svg" not in content:
        content = (
            content[:title_end]
            + "\n[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/microsoft/autogen/blob/main/notebook/"
            + notebook_name
            + ")"
            + content[title_end:]
        )

    # Rewrite the content as
    # ---
    # front_matter
    # ---
    # content
    new_content = f"---\n{front_matter}\n---\n{content}"
    with open(rendered_mdx, "w", encoding="utf-8") as f:
        f.write(new_content)


def path(path_str: str) -> Path:
    """Return a Path object."""
    return Path(path_str)


def collect_notebooks(notebook_directory: Path, website_directory: Path) -> typing.List[Path]:
    notebooks = list(notebook_directory.glob("*.ipynb"))
    notebooks.extend(list(website_directory.glob("docs/**/*.ipynb")))
    return notebooks


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
    parser.add_argument("--workers", help="Number of workers to use", type=int, default=-1)

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--quarto-bin", help="Path to quarto binary", default="quarto")
    render_parser.add_argument("--dry-run", help="Don't render", action="store_true")
    render_parser.add_argument("notebooks", type=path, nargs="*", default=None)

    test_parser = subparsers.add_parser("test")
    test_parser.add_argument("--timeout", help="Timeout for each notebook", type=int, default=60)
    test_parser.add_argument("--exit-on-first-fail", "-e", help="Exit after first test fail", action="store_true")
    test_parser.add_argument("notebooks", type=path, nargs="*", default=None)

    args = parser.parse_args()
    if args.workers == -1:
        args.workers = None

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
            print(f"{colored('[Skip]', 'yellow')} {colored(notebook.name, 'blue')}: {reason}")
        else:
            filtered_notebooks.append(notebook)

    print(f"Processing {len(filtered_notebooks)} notebook{'s' if len(filtered_notebooks) != 1 else ''}...")

    if args.subcommand == "test":
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
                        print(
                            f"{colored('[Error]', 'red')} {colored(notebook.name, 'blue')}: {optional_error_or_skip.error_name}"
                        )

                    else:
                        print("-" * 80)
                        print(
                            f"{colored('[Error]', 'red')} {colored(notebook.name, 'blue')}: {optional_error_or_skip.error_name} - {optional_error_or_skip.error_value}"
                        )
                        print(optional_error_or_skip.traceback)
                        print("-" * 80)
                    if args.exit_on_first_fail:
                        sys.exit(1)
                    failure = True
                elif isinstance(optional_error_or_skip, NotebookSkip):
                    print(
                        f"{colored('[Skip]', 'yellow')} {colored(notebook.name, 'blue')}: {optional_error_or_skip.reason}"
                    )
                else:
                    print(f"{colored('[OK]', 'green')} {colored(notebook.name, 'blue')}")

        if failure:
            sys.exit(1)

    elif args.subcommand == "render":
        check_quarto_bin(args.quarto_bin)

        if not notebooks_target_dir(args.website_directory).exists():
            notebooks_target_dir(args.website_directory).mkdir(parents=True)

        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(
                    process_notebook, f, args.website_directory, args.notebook_directory, args.quarto_bin, args.dry_run
                )
                for f in filtered_notebooks
            ]
            for future in concurrent.futures.as_completed(futures):
                print(future.result())
    else:
        print("Unknown subcommand")
        sys.exit(1)


if __name__ == "__main__":
    main()
