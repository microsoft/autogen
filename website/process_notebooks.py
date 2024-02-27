import sys
from pathlib import Path
import subprocess
import argparse
import shutil
import json
import typing
import concurrent.futures

try:
    import yaml
except ImportError:
    print("pyyaml not found.\n\nPlease install pyyaml:\n\tpip install pyyaml\n")
    sys.exit(1)

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


def check_quarto_bin(quarto_bin: str = "quarto"):
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


def process_notebook(src_notebook: Path, dest_dir: Path, quarto_bin: str, dry_run: bool) -> str:
    """Process a single notebook."""
    reason_or_none = skip_reason_or_none_if_ok(src_notebook)
    if reason_or_none:
        return colored(f"Skipping {src_notebook.name}, reason: {reason_or_none}", "yellow")

    target_mdx_file = dest_dir / f"{src_notebook.stem}.mdx"
    intermediate_notebook = dest_dir / f"{src_notebook.stem}.ipynb"

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
        return colored(f"Failed to render {intermediate_notebook}", "red") + f"\n{result.stderr}" + f"\n{result.stdout}"

    # Unlink intermediate files
    intermediate_notebook.unlink()

    if "extra_files_to_copy" in front_matter:
        for file in front_matter["extra_files_to_copy"]:
            (dest_dir / file).unlink()

    # Post process the file
    post_process_mdx(target_mdx_file)

    return colored(f"Processed {src_notebook.name}", "green")


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


def main():
    script_dir = Path(__file__).parent.absolute()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--notebook-directory",
        type=path,
        help="Directory containing notebooks to process",
        default=script_dir / "../notebook",
    )
    parser.add_argument(
        "--website-directory", type=path, help="Root directory of docusarus website", default=script_dir
    )
    parser.add_argument("--quarto-bin", help="Path to quarto binary", default="quarto")
    parser.add_argument("--dry-run", help="Don't render", action="store_true")
    parser.add_argument("--workers", help="Number of workers to use", type=int, default=-1)

    args = parser.parse_args()

    if args.workers == -1:
        args.workers = None

    check_quarto_bin(args.quarto_bin)

    if not notebooks_target_dir(args.website_directory).exists():
        notebooks_target_dir(args.website_directory).mkdir(parents=True)

    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                process_notebook, f, notebooks_target_dir(args.website_directory), args.quarto_bin, args.dry_run
            )
            for f in args.notebook_directory.glob("*.ipynb")
        ]
        for future in concurrent.futures.as_completed(futures):
            print(future.result())


if __name__ == "__main__":
    main()
