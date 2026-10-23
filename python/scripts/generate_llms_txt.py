#!/usr/bin/env python3
"""Generate llms.txt and llms-full.txt for AutoGen documentation.

This script reads documentation source files (Markdown and Jupyter notebooks)
and produces LLM-friendly text files following the llms.txt specification
(https://llmstxt.org/).

Usage:
    python scripts/generate_llms_txt.py

Output:
    docs/src/llms.txt       - Structured index of documentation pages
    docs/src/llms-full.txt  - Full concatenated documentation text
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DOCS_SRC = Path(__file__).resolve().parent.parent / "docs" / "src"
BASE_URL = "https://microsoft.github.io/autogen/stable"

GUIDE_SECTIONS = [
    {
        "title": "AgentChat",
        "description": "High-level API for building multi-agent applications",
        "path": "user-guide/agentchat-user-guide",
    },
]


def extract_notebook_text(path: Path) -> str:
    """Extract markdown and code cells from a Jupyter notebook."""
    with open(path, encoding="utf-8") as f:
        nb = json.load(f)

    parts: list[str] = []
    for cell in nb.get("cells", []):
        source = "".join(cell.get("source", []))
        if not source.strip():
            continue
        if cell["cell_type"] == "markdown":
            parts.append(source)
        elif cell["cell_type"] == "code":
            parts.append(f"```python\n{source}\n```")
    return "\n\n".join(parts)


def extract_markdown_text(path: Path) -> str:
    """Read a markdown file, stripping front matter."""
    text = path.read_text(encoding="utf-8")
    # Strip YAML front matter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3 :].lstrip("\n")
    return text


def get_title(text: str) -> str:
    """Extract the first heading from text."""
    for line in text.splitlines():
        m = re.match(r"^#\s+(.+)", line)
        if m:
            # Strip MyST/Sphinx directives from title
            title = m.group(1).strip()
            title = re.sub(r"\{[^}]+\}`[^`]*`", "", title).strip()
            return title
    return ""


def collect_docs(section_path: Path) -> list[tuple[Path, str]]:
    """Collect all .md and .ipynb files in order, returning (path, text) pairs."""
    results: list[tuple[Path, str]] = []

    # Process index first if it exists
    index = section_path / "index.md"
    if index.exists():
        results.append((index, extract_markdown_text(index)))

    # Then all other files recursively, sorted for deterministic output
    for path in sorted(section_path.rglob("*")):
        if path == index:
            continue
        if path.suffix == ".md":
            results.append((path, extract_markdown_text(path)))
        elif path.suffix == ".ipynb":
            results.append((path, extract_notebook_text(path)))

    return results


def make_url(section_url_path: str, file_path: Path, section_root: Path) -> str:
    """Convert a file path to its documentation URL."""
    rel = file_path.relative_to(section_root)
    # Change extension to .html
    url_path = str(rel.with_suffix(".html"))
    return f"{BASE_URL}/{section_url_path}/{url_path}"


def generate() -> None:
    """Generate llms.txt and llms-full.txt."""
    index_lines: list[str] = [
        "# AutoGen",
        "",
        "> AutoGen is an open-source framework for building multi-agent AI applications.",
        "> It provides tools for creating agents that can collaborate, use tools, and solve",
        "> complex tasks through structured conversations.",
        "",
    ]
    full_parts: list[str] = [
        "# AutoGen Documentation\n",
    ]

    for section in GUIDE_SECTIONS:
        section_root = DOCS_SRC / section["path"]
        if not section_root.exists():
            print(f"Warning: {section_root} not found, skipping", file=sys.stderr)
            continue

        index_lines.append(f"## {section['title']}")
        index_lines.append("")
        index_lines.append(f"{section['description']}")
        index_lines.append("")

        docs = collect_docs(section_root)
        for path, text in docs:
            title = get_title(text) or path.stem.replace("-", " ").title()
            url = make_url(section["path"], path, section_root)
            index_lines.append(f"- [{title}]({url})")

            full_parts.append(f"---\n\n## {title}\n\nSource: {url}\n\n{text}\n")

        index_lines.append("")

    # Write index
    llms_txt = DOCS_SRC / "llms.txt"
    llms_txt.write_text("\n".join(index_lines), encoding="utf-8")
    print(f"Generated {llms_txt}")

    # Write full text
    llms_full = DOCS_SRC / "llms-full.txt"
    llms_full.write_text("\n".join(full_parts), encoding="utf-8")
    print(f"Generated {llms_full}")


if __name__ == "__main__":
    generate()
