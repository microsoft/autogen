"""Sphinx extension to generate llms.txt for AutoGen documentation.

The llms.txt file follows the llms.txt standard (https://llmstxt.org/) which provides
a structured index of documentation content for Large Language Models (LLMs).

A companion llms-full.txt file is also generated, containing the same index followed
by the full plain-text body of every indexed page.
"""

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional

from sphinx.application import Sphinx
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.util import logging

logger = logging.getLogger(__name__)

# Default documentation sections (display title → docname prefix), in display order.
# Override via ``llms_txt_sections`` in conf.py.
_DEFAULT_SECTIONS: Dict[str, str] = {
    "AutoGen Studio": "user-guide/autogenstudio-user-guide",
    "AgentChat": "user-guide/agentchat-user-guide",
    "Core": "user-guide/core-user-guide",
    "Extensions": "user-guide/extensions-user-guide",
}


class _BodyTextExtractor(HTMLParser):
    """Extract readable text from the main content area of a Sphinx HTML page.

    Only text inside ``<article>`` or ``<main>`` tags is captured; ``<script>``,
    ``<style>``, ``<nav>``, ``<header>``, and ``<footer>`` content is skipped.
    """

    _SKIP_TAGS = frozenset({"script", "style", "nav", "header", "footer"})

    def __init__(self) -> None:
        super().__init__()
        self._in_main = 0
        self._in_skip = 0
        self._chunks: List[str] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in ("article", "main"):
            self._in_main += 1
        if tag in self._SKIP_TAGS:
            self._in_skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("article", "main"):
            self._in_main = max(0, self._in_main - 1)
        if tag in self._SKIP_TAGS:
            self._in_skip = max(0, self._in_skip - 1)

    def handle_data(self, data: str) -> None:
        if self._in_main and not self._in_skip:
            self._chunks.append(data)

    def get_text(self) -> str:
        text = "".join(self._chunks)
        # Collapse runs of more than two blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def _get_sections(app: Sphinx) -> Dict[str, str]:
    """Return the sections mapping, preferring ``llms_txt_sections`` from conf.py."""
    return app.config.llms_txt_sections or _DEFAULT_SECTIONS


def _page_url(app: Sphinx, docname: str) -> str:
    """Return the full URL for a documentation page.

    Uses ``llms_txt_base_url`` from conf.py when set; otherwise falls back to
    ``html_baseurl``.  Emits a warning when the resolved base URL is
    root-relative rather than absolute, because llms.txt consumers expect
    fully-qualified links.
    """
    base_url = (app.config.llms_txt_base_url or app.config.html_baseurl or "").rstrip("/")
    if base_url and not base_url.startswith(("http://", "https://")):
        logger.warning(
            "llms_txt: base URL %r is not absolute. "
            "Set 'llms_txt_base_url' in conf.py to a fully-qualified URL "
            "so that llms.txt contains absolute links.",
            base_url,
        )
    target_uri = app.builder.get_target_uri(docname)  # type: ignore[attr-defined]
    return f"{base_url}/{target_uri}"


def _page_title(app: Sphinx, docname: str) -> Optional[str]:
    """Return the plain-text title for a documentation page, or *None*."""
    title_node = app.env.titles.get(docname)
    if title_node is not None:
        return title_node.astext()
    return None


def _page_description(app: Sphinx, docname: str) -> Optional[str]:
    """Return a one-line description for a documentation page, or *None*.

    The description is taken from the MyST ``html_meta`` frontmatter field
    ``"description lang=en"`` when present.
    """
    metadata = app.env.metadata.get(docname, {})
    myst_config = metadata.get("myst", {})
    if not isinstance(myst_config, dict):
        return None
    html_meta = myst_config.get("html_meta", {})
    if not isinstance(html_meta, dict):
        return None
    for key, value in html_meta.items():
        if "description" in str(key).lower():
            # Collapse any embedded newlines or extra whitespace
            return " ".join(str(value).split())
    return None


def _page_content(app: Sphinx, docname: str) -> Optional[str]:
    """Return the plain-text body of a built HTML page, or *None*.

    Reads the HTML file that Sphinx wrote to ``app.outdir`` and extracts the
    text inside the ``<article>`` / ``<main>`` element, stripping navigation,
    scripts, and other chrome.  Returns *None* if the file does not exist or
    yields no extractable text.
    """
    target_uri = app.builder.get_target_uri(docname)  # type: ignore[attr-defined]
    html_path = Path(app.outdir) / target_uri
    if not html_path.exists():
        return None
    html_text = html_path.read_text(encoding="utf-8")
    extractor = _BodyTextExtractor()
    extractor.feed(html_text)
    text = extractor.get_text()
    return text if text else None


def _build_llms_txt(app: Sphinx) -> str:
    """Assemble and return the llms.txt index content as a string."""
    all_docs = sorted(app.env.found_docs)
    sections = _get_sections(app)

    project_title = app.config.html_title or app.config.project
    description = app.config.llms_txt_description or app.config.project

    lines = [
        f"# {project_title}",
        "",
        f"> {description}",
        "",
    ]

    for section_title, prefix in sections.items():
        section_docs = [doc for doc in all_docs if doc.startswith(prefix)]
        if not section_docs:
            continue

        lines.append(f"## {section_title}")
        lines.append("")

        for docname in section_docs:
            title = _page_title(app, docname)
            if not title:
                continue

            url = _page_url(app, docname)
            doc_description = _page_description(app, docname)

            if doc_description:
                lines.append(f"- [{title}]({url}): {doc_description}")
            else:
                lines.append(f"- [{title}]({url})")

        lines.append("")

    return "\n".join(lines)


def _build_llms_full_txt(app: Sphinx) -> str:
    """Assemble and return llms-full.txt: the index followed by each page's content.

    Pages whose HTML file cannot be read (e.g. notebooks or pages without a
    rendered ``<article>`` element) are listed in the index but their content
    block is omitted from this file.
    """
    all_docs = sorted(app.env.found_docs)
    sections = _get_sections(app)

    parts = [_build_llms_txt(app), ""]

    for _section_title, prefix in sections.items():
        section_docs = [doc for doc in all_docs if doc.startswith(prefix)]
        for docname in section_docs:
            title = _page_title(app, docname)
            if not title:
                continue

            url = _page_url(app, docname)
            content = _page_content(app, docname)
            if content:
                parts.append(f"## {title}")
                parts.append(f"URL: {url}")
                parts.append("")
                parts.append(content)
                parts.append("")

    return "\n".join(parts)


def generate_llms_txt(app: Sphinx, exception: Optional[Exception]) -> None:
    """Generate ``llms.txt`` and ``llms-full.txt`` after the HTML build finishes.

    This function is wired to Sphinx's ``build-finished`` event.  It is a
    no-op when an exception occurred during the build or when a non-HTML
    builder is in use.
    """
    if exception:
        return
    if not isinstance(app.builder, StandaloneHTMLBuilder):
        return

    content = _build_llms_txt(app)
    output_path = Path(app.outdir) / "llms.txt"
    output_path.write_text(content, encoding="utf-8")
    logger.info(f"llms.txt generated at {output_path}")

    full_content = _build_llms_full_txt(app)
    full_output_path = Path(app.outdir) / "llms-full.txt"
    full_output_path.write_text(full_content, encoding="utf-8")
    logger.info(f"llms-full.txt generated at {full_output_path}")


def setup(app: Sphinx) -> Dict[str, Any]:
    """Register the extension with the Sphinx application."""
    app.add_config_value("llms_txt_base_url", default=None, rebuild="html")
    app.add_config_value("llms_txt_sections", default=None, rebuild="html")
    app.add_config_value("llms_txt_description", default=None, rebuild="html")
    app.connect("build-finished", generate_llms_txt)

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
